import typing
import janome.tokenizer as jt
from . import dic

tokenizer: jt.Tokenizer = None

def generate_tokenizer():
    import janome.dic
    from janome.sysdic import connections
    import tempfile

    tokenizer = jt.Tokenizer()

    abc_entries = dic.generate_abc_dic(
        sysdic = tokenizer.sys_dic.entries.values()
    )

    with tempfile.NamedTemporaryFile(mode = "w") as user_dict_tf:
        for entry in abc_entries:
            user_dict_tf.write(",".join(map(str, entry)))
            user_dict_tf.write("\n")
        # === END FOR entry ===

        tokenizer.user_dic = janome.dic.UserDictionary(
            user_dict_tf.name, 
            "utf8", "ipadic",
            connections
        )
    # === END WITH user_dict ===

    return tokenizer
# === END ===

def tokenize(
    sentences: typing.Iterable[typing.Iterable[str]]
) -> typing.Tuple[
    typing.List[typing.List["depccg.tokens.Token"]], 
    typing.List[str]
]:
    import depccg.tokens

    global tokenizer 

    if tokenizer:
        pass
    else:
        tokenizer = generate_tokenizer()
    # === END IF ===

    res = []
    raw_sentences = []

    for sentence in sentences:
        sentence = ''.join(sentence)
        tokenized = tokenizer.tokenize(sentence)
        tokens = []

        for token in tokenized:
            pos, pos1, pos2, pos3 = token.part_of_speech.split(',')
            token = depccg.tokens.Token(
                word=token.surface,
                surf=token.surface,
                pos=pos,
                pos1=pos1,
                pos2=pos2,
                pos3=pos3,
                inflectionForm=token.infl_form,
                inflectionType=token.infl_type,
                reading=token.reading,
                base=token.base_form
            )
            tokens.append(token)
        raw_sentence = [token.surface for token in tokenized]
        res.append(tokens)
        raw_sentences.append(raw_sentence)

    return res, raw_sentences
# === END ===