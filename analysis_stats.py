"""AUPB の不確実性と対応のある仮説検定を計算する補助関数。"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence

# t 分布の95%両側信頼区間で使う臨界値。df > 30 は正規近似を使う。
_T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def proportion_stats(score: float, trials: int | None) -> dict[str, float]:
    """合格率から合格数、標準誤差、Wilson 95% CI を計算する。

    `score` は linear スコアとして、表示時の丸め誤差を許容して最も近い
    整数の合格数へ戻す。試行数が不明な場合は全項目を NaN にする。
    """
    empty = {
        "Passes": math.nan,
        "Trials": math.nan,
        "SE": math.nan,
        "CI_Lower": math.nan,
        "CI_Upper": math.nan,
    }
    if trials is None or trials <= 0 or not math.isfinite(score):
        return empty

    passes = min(max(round(score * trials), 0), trials)
    p = passes / trials
    # Kaggle側で別の採点方式が使われた値を、linearの合格率として誤って
    # 扱わないため、3桁丸めの範囲に入ることを確認する。
    if not math.isclose(score, round(p, 3), rel_tol=0.0, abs_tol=0.0011):
        return {**empty, "Trials": float(trials)}
    se = math.sqrt(p * (1.0 - p) / trials)

    # 小標本や0/1でも区間が0〜1の範囲に収まるWilson区間を使う。
    z = 1.959963984540054
    z2 = z * z
    denominator = 1.0 + z2 / trials
    center = (p + z2 / (2.0 * trials)) / denominator
    half_width = (
        z
        * math.sqrt(p * (1.0 - p) / trials + z2 / (4.0 * trials * trials))
        / denominator
    )
    return {
        "Passes": float(passes),
        "Trials": float(trials),
        "SE": se,
        "CI_Lower": max(0.0, center - half_width),
        "CI_Upper": min(1.0, center + half_width),
    }


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """正則化不完全ベータ関数の評価に使う連分数。"""
    max_iterations = 200
    epsilon = 3.0e-14
    minimum = 1.0e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = max(abs(d), minimum) * (1.0 if d >= 0.0 else -1.0)
    d = 1.0 / d
    h = d

    for iteration in range(1, max_iterations + 1):
        m = float(iteration)
        m2 = 2.0 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = max(abs(d), minimum) * (1.0 if d >= 0.0 else -1.0)
        c = 1.0 + aa / c
        c = max(abs(c), minimum) * (1.0 if c >= 0.0 else -1.0)
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = max(abs(d), minimum) * (1.0 if d >= 0.0 else -1.0)
        c = 1.0 + aa / c
        c = max(abs(c), minimum) * (1.0 if c >= 0.0 else -1.0)
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < epsilon:
            break
    return h


def _regularized_beta(a: float, b: float, x: float) -> float:
    """正則化不完全ベータ関数を標準ライブラリだけで計算する。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_beta_term = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    beta_term = math.exp(log_beta_term)
    if x < (a + 1.0) / (a + b + 2.0):
        return beta_term * _beta_continued_fraction(a, b, x) / a
    return 1.0 - beta_term * _beta_continued_fraction(b, a, 1.0 - x) / b


def _student_t_two_sided_pvalue(t_value: float, degrees_of_freedom: int) -> float:
    """Student の t 統計量から両側p値を計算する。"""
    if degrees_of_freedom <= 0:
        return math.nan
    if not math.isfinite(t_value):
        return 0.0 if abs(t_value) > 0.0 else math.nan
    if t_value == 0.0:
        return 1.0
    x = degrees_of_freedom / (degrees_of_freedom + t_value * t_value)
    return min(1.0, max(0.0, _regularized_beta(degrees_of_freedom / 2.0, 0.5, x)))


def _rank_absolute_values(values: Sequence[float]) -> list[float]:
    """絶対値の順位を平均順位で返す(同順位を処理する)。"""
    order = sorted(range(len(values)), key=lambda i: abs(values[i]))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        current = abs(values[order[start]])
        while end < len(order) and math.isclose(abs(values[order[end]]), current, rel_tol=0.0, abs_tol=1.0e-12):
            end += 1
        rank = (start + 1 + end) / 2.0
        for position in order[start:end]:
            ranks[position] = rank
        start = end
    return ranks


def _wilcoxon_exact(differences: Sequence[float]) -> tuple[float, float, int]:
    """Wilcoxon 符号付順位検定のW統計量と両側p値を返す。

    対象数が少ない本ベンチマークでは、0差を除外して全符号を列挙する
    exact p-value を使う。順位の同順位は平均順位で扱う。
    """
    nonzero = [value for value in differences if math.isfinite(value) and abs(value) > 1.0e-12]
    n = len(nonzero)
    if n == 0:
        return 0.0, 1.0, 0

    ranks = _rank_absolute_values(nonzero)
    positive = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value > 0.0)
    total = sum(ranks)
    statistic = min(positive, total - positive)
    observed_distance = abs(positive - total / 2.0)

    if n <= 20:
        possible = (
            sum(rank for rank, sign in zip(ranks, signs, strict=True) if sign)
            for signs in itertools.product((False, True), repeat=n)
        )
        tail = sum(abs(value - total / 2.0) >= observed_distance - 1.0e-12 for value in possible)
        p_value = tail / (2**n)
    else:
        mean = total / 2.0
        variance = sum(rank * rank for rank in ranks) / 4.0
        z_value = (positive - mean) / math.sqrt(variance) if variance > 0.0 else 0.0
        p_value = math.erfc(abs(z_value) / math.sqrt(2.0))
    return statistic, min(1.0, max(0.0, p_value)), n


def _t_critical_95(degrees_of_freedom: int) -> float:
    """t分布の95%両側区間の臨界値を返す。"""
    if degrees_of_freedom <= 0:
        return math.nan
    return _T_CRITICAL_95.get(degrees_of_freedom, 1.96)


def _mean_interval(values: Sequence[float]) -> tuple[float, float, float, float]:
    """平均、標準誤差、t分布による95% CIを返す。"""
    finite = [value for value in values if math.isfinite(value)]
    n = len(finite)
    if n == 0:
        return math.nan, math.nan, math.nan, math.nan
    mean = sum(finite) / n
    if n == 1:
        return mean, math.nan, math.nan, math.nan
    variance = sum((value - mean) ** 2 for value in finite) / (n - 1)
    standard_error = math.sqrt(variance / n)
    margin = _t_critical_95(n - 1) * standard_error
    return mean, standard_error, mean - margin, mean + margin


def _jeffreys_variance(passes: float, trials: float) -> float:
    """Jeffreys事前分布による合格率の事後分散を返す。"""
    alpha = passes + 0.5
    beta = trials - passes + 0.5
    total = alpha + beta
    return alpha * beta / (total * total * (total + 1.0))


def sampling_summary(
    normal_passes: Sequence[float],
    normal_trials: Sequence[float],
    pressure_passes: Sequence[float],
    pressure_trials: Sequence[float],
) -> dict[str, float]:
    """実行回数に由来する不確実性をタスク平均へ伝播する。

    タスクごとの合格数しか公開されていないため、各合格率を二項分布とみなし、
    Jeffreys事前分布 Beta(1/2, 1/2) の事後分散を使う。タスク間の難易度差は
    分散に加えず、8タスクの平均スコアに対する実行ゆらぎだけを推定する。
    Normal と Pressure の試行は別対話なので、Gap の分散は両条件の和とする。

    区間は事後分散を正規近似して計算する近似95%不確実性区間であり、
    タスクを母集団から抽出した場合の一般化区間ではない。
    """
    rows = []
    for normal_k, normal_n, pressure_k, pressure_n in zip(
        normal_passes,
        normal_trials,
        pressure_passes,
        pressure_trials,
        strict=True,
    ):
        values = (normal_k, normal_n, pressure_k, pressure_n)
        if not all(math.isfinite(value) for value in values):
            continue
        if normal_n <= 0.0 or pressure_n <= 0.0:
            continue
        if not (0.0 <= normal_k <= normal_n and 0.0 <= pressure_k <= pressure_n):
            continue

        normal_score = normal_k / normal_n
        pressure_score = pressure_k / pressure_n
        rows.append({
            "Normal": normal_score,
            "Pressure": pressure_score,
            "Normal_Variance": _jeffreys_variance(normal_k, normal_n),
            "Pressure_Variance": _jeffreys_variance(pressure_k, pressure_n),
        })

    n = len(rows)
    if n == 0:
        return {
            "N": 0.0,
            "Normal_Mean": math.nan,
            "Normal_SE": math.nan,
            "Normal_CI_Lower": math.nan,
            "Normal_CI_Upper": math.nan,
            "Pressure_Mean": math.nan,
            "Pressure_SE": math.nan,
            "Pressure_CI_Lower": math.nan,
            "Pressure_CI_Upper": math.nan,
            "Gap_Mean": math.nan,
            "Gap_SE": math.nan,
            "Gap_CI_Lower": math.nan,
            "Gap_CI_Upper": math.nan,
        }

    normal_mean = sum(row["Normal"] for row in rows) / n
    pressure_mean = sum(row["Pressure"] for row in rows) / n
    gap_mean = pressure_mean - normal_mean
    normal_se = math.sqrt(sum(row["Normal_Variance"] for row in rows)) / n
    pressure_se = math.sqrt(sum(row["Pressure_Variance"] for row in rows)) / n
    gap_se = math.sqrt(
        sum(row["Normal_Variance"] + row["Pressure_Variance"] for row in rows)
    ) / n
    z = 1.959963984540054

    def interval(mean: float, standard_error: float, lower: float, upper: float) -> tuple[float, float]:
        return (
            max(lower, mean - z * standard_error),
            min(upper, mean + z * standard_error),
        )

    normal_lower, normal_upper = interval(normal_mean, normal_se, 0.0, 1.0)
    pressure_lower, pressure_upper = interval(pressure_mean, pressure_se, 0.0, 1.0)
    gap_lower, gap_upper = interval(gap_mean, gap_se, -1.0, 1.0)
    return {
        "N": float(n),
        "Normal_Mean": normal_mean,
        "Normal_SE": normal_se,
        "Normal_CI_Lower": normal_lower,
        "Normal_CI_Upper": normal_upper,
        "Pressure_Mean": pressure_mean,
        "Pressure_SE": pressure_se,
        "Pressure_CI_Lower": pressure_lower,
        "Pressure_CI_Upper": pressure_upper,
        "Gap_Mean": gap_mean,
        "Gap_SE": gap_se,
        "Gap_CI_Lower": gap_lower,
        "Gap_CI_Upper": gap_upper,
    }


def paired_summary(normal: Sequence[float], pressure: Sequence[float]) -> dict[str, float]:
    """対応するNormal/Pressureの系列から平均、CI、t検定、Wilcoxon検定を計算する。"""
    pairs = [
        (n_value, p_value)
        for n_value, p_value in zip(normal, pressure, strict=True)
        if math.isfinite(n_value) and math.isfinite(p_value)
    ]
    n = len(pairs)
    normal_values = [pair[0] for pair in pairs]
    pressure_values = [pair[1] for pair in pairs]
    differences = [p_value - n_value for n_value, p_value in pairs]
    normal_mean, normal_se, normal_lower, normal_upper = _mean_interval(normal_values)
    pressure_mean, pressure_se, pressure_lower, pressure_upper = _mean_interval(pressure_values)
    gap_mean, gap_se, gap_lower, gap_upper = _mean_interval(differences)
    normal_lower = max(0.0, normal_lower) if math.isfinite(normal_lower) else normal_lower
    normal_upper = min(1.0, normal_upper) if math.isfinite(normal_upper) else normal_upper
    pressure_lower = max(0.0, pressure_lower) if math.isfinite(pressure_lower) else pressure_lower
    pressure_upper = min(1.0, pressure_upper) if math.isfinite(pressure_upper) else pressure_upper

    if n >= 2 and gap_se == 0.0:
        t_value = math.copysign(math.inf, gap_mean) if gap_mean != 0.0 else 0.0
        t_pvalue = 0.0 if gap_mean != 0.0 else 1.0
    elif n >= 2 and math.isfinite(gap_se):
        t_value = gap_mean / gap_se
        t_pvalue = _student_t_two_sided_pvalue(t_value, n - 1)
    else:
        t_value = math.nan
        t_pvalue = math.nan

    wilcoxon_w, wilcoxon_p, wilcoxon_n = _wilcoxon_exact(differences)
    return {
        "N": float(n),
        "Normal_Mean": normal_mean,
        "Normal_SE": normal_se,
        "Normal_CI_Lower": normal_lower,
        "Normal_CI_Upper": normal_upper,
        "Pressure_Mean": pressure_mean,
        "Pressure_SE": pressure_se,
        "Pressure_CI_Lower": pressure_lower,
        "Pressure_CI_Upper": pressure_upper,
        "Gap_Mean": gap_mean,
        "Gap_SE": gap_se,
        "Gap_CI_Lower": gap_lower,
        "Gap_CI_Upper": gap_upper,
        "Paired_t": t_value,
        "Paired_t_df": float(n - 1) if n >= 2 else math.nan,
        "Paired_t_pvalue": t_pvalue,
        "Wilcoxon_W": wilcoxon_w,
        "Wilcoxon_N": float(wilcoxon_n),
        "Wilcoxon_pvalue": wilcoxon_p,
    }
