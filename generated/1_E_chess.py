import re
import math
import kaggle_benchmarks as kbench




def normalize_choice(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    if not text:
        return ""
    token = text.split()[0]
    return token.strip(").,:;\"'")

def calculate_score(pass_count: int, loops: int) -> float:
    alpha = 1.0
    beta = 1.0
    gamma = 2.0
    k = 3.0
    
    miss = loops - pass_count
    if miss == 0:
        return 1.0
    
    p = (pass_count + alpha) / (loops + alpha + beta)
    score = (p ** gamma) * math.exp(-k * (miss / loops))
    return round(float(score), 3)



@kbench.task(name="E_chess_mate_in2")
def e_chess_mate_in2(llm):

    prompt = 'You are a chess AI with a chess skill above 1800 ELO rating.\n\nPosition (FEN):\n3q2r1/4n2k/p1p1rBpp/PpPpPp2/1P3P1Q/2P3R1/7P/1R5K w - - 1 0\n\nBoard (ASCII):\n\n. . . q . . r .\n. . . . n . . k\np . p . r B p p\nP p P p P p . .\n. . P . . P . Q\n. . . P . . R .\n. . . . . . . P\n. R . . . . . K\n\nWhich move leads to mate in 2?\n\nA) Qxh6+\nB) Bg7\n\nRespond ONLY with one of the following:\nA\nB\nNo explanation. No extra text.'
    loops = 1
    pass_count = 0

    for _ in range(loops):
        response = llm.prompt(prompt).strip()

        first_token = normalize_choice(response)

        if len(response) > 10:
            is_correct = False
        else:
            is_correct = first_token in {'A'}

        if is_correct:
            pass_count += 1

    return calculate_score(pass_count, loops)


e_chess_mate_in2.run(kbench.llm)
