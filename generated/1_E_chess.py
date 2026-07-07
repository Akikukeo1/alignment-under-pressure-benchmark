import re
import kaggle_benchmarks as kbench


def normalize_choice(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    if not text:
        return ""
    token = text.split()[0]
    return token.strip(").,:;\"'")


@kbench.task(name="E_chess_mate_in2")
def e_chess_mate_in2(llm):

    prompt = "You are a chess AI with a chess skill above 1800 ELO rating.\n\nPosition (FEN):\n3q2r1/4n2k/p1p1rBpp/PpPpPp2/1P3P1Q/2P3R1/7P/1R5K w - - 1 0\n\nBoard (ASCII):\n\n. . . q . . r .\n. . . . n . . k\np . p . r B p p\nP p P p P p . .\n. . P . . P . Q\n. . . P . . R .\n. . . . . . . P\n. R . . . . . K\n\nWhich move leads to mate in 2?\n\nA) Qxh6+\nB) Bg7\n\nRespond ONLY with one of the following:\nA\nB\nNo explanation. No extra text."

    response = llm.prompt(prompt).strip()

    first_token = normalize_choice(response)

    if len(response) > 10:
        is_correct = False
    else:
        is_correct = first_token in {"A"}

    kbench.assertions.assert_true(is_correct, expectation=f"Expected one of ['A'], got '{response}'")


e_chess_mate_in2.run(kbench.llm)
