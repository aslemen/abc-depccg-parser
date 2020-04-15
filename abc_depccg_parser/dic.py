import typing
import itertools
import functools
import re
import sys
import io

from collections import namedtuple

JanomeLexEntry = namedtuple(
    "JanomeLexEntry",
    (
        "surface", "left_id", "right_id", "cost",
        "part_of_speech",
        "infl_type", "infl_form", "base_form", "reading", "phonetic"
    )
)

def print_dic_as_csv() -> str:
    with io.StringIO() as sf:
        dump_dic_as_csv(sf)
        return sf.getvalue
    # === END WITH sf===
# === END ===

def dump_dic_as_csv(
    stream: typing.TextIO = sys.stdout
) -> typing.NoReturn:
    for entry in generate_abc_dic():
        stream.write(convert_JanomeLexEntry_to_CSV(entry))
        stream.write("\n")
    # === END FOR entry ===
# === END ===

def convert_JanomeLexEntry_to_CSV(
    entry: JanomeLexEntry
) -> str:
    return ", ".join(map(str, entry))
# === END ===

@functools.lru_cache(maxsize = 16)
def generate_abc_dic(
    sysdic: typing.Optional[typing.Iterable[typing.Iterable[typing.Any]]] = None
) -> typing.Set[JanomeLexEntry]:
    """
    Generate custom Janome lexical entries for this parser.

    Parameters
    ----------
    sysdic : internal list of lexical entries in janome.dic.SystemDictionary, optional
        An iterable of internal representation of Janome lexical entries.
        Optional.
        If not given, this function will retrive one from Janome.

        Giving a reference to the system lexical entries is recommended 
            for performance reasons
            whenever you have obtained a relevant instance 
            which contains a Janome system dictionary.

    Returns
    -------
    abc_entries : set of JanomeLexEntry
        Our custom lexical entries.

    Notes
    -----
    The authors choose a set, rather than a generator, for the returning result
        since this subroutine is intended to be externally cached (not implemented yet).

    Examples
    --------
    >>> import janome.tokenizer as jt
    ... tokenizer = jt.Tokenizer()
    ... abc_entries = dic.generate_abc_dic(
    ...     sysdic = tokenizer.sys_dic.entries.values()
    ... )
    ... next(iter(abc_entries)).surface
    "筈もあれ"
    """

    if sysdic:
        return _gen_abc_dic(sysdic)
    else:
        import janome.dic
        from janome.sysdic import (
            all_fstdata, entries, mmap_entries, 
            connections, chardef, unknowns
        )

        janome_sys_dic = janome.dic.SystemDictionary(
            all_fstdata(), 
            entries(None), 
            connections, 
            chardef.DATA, 
            unknowns.DATA
        )

        return set(_gen_abc_dic(janome_sys_dic.entries.values()))
    # === END IF ===
# === END ===

def _gen_abc_dic(
    sysdic: typing.Iterable[typing.Iterable[typing.Any]]
) -> typing.Set[JanomeLexEntry]:
    """
    An internal function that actually generates custom lexical entries.

    List of custom entries:
    
    - {だろ, でしょ}う
    - はず{が, も, は, の}{ない, ある, ありません}
    - かもしれない
    - {なければ, なきゃ, ないと, んと}{ならない, いけない}
    - ては{ならない, いけない}

    Parameters
    ----------
    sysdic : internal list of lexical entries in janome.dic.SystemDictionary, optional

    Yields
    -------
    abc_entry : JanomeLexEntry
        One of our custom lexical entries.
    """

    # ------
    # collecting atomic morphemes
    # ------

    # Note: Lists of found morphemes should be fixed as tuples
    #       rather than iterators so that they can be made use of
    #       (possibly) multiple times.

    morphemes: typing.Dict[str, typing.Tuple[JanomeLexEntry]] = {
        # -- はず（名詞，非自立）
        "hazu": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^(はず|ハズ|筈)$", e[7]) and re.match(r"名詞,非自立", e[4])
        ),
        # -- か（終助詞）
        "ka": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^か$", e[7])
        ),
        # -- ない（形容詞）
        "nai_adj": tuple(
            JanomeLexEntry(*e) 
            for e in sysdic
            if re.match(r"^(ない|無い)$", e[7]) and re.match(r"形容詞", e[4])
        ),
        # -- ない（助動詞）
        # -- ん（助動詞）
        # -- ぬ（否定助動詞）
        "nai_aux": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if (
                re.match(r"^ん$", e[7]) 
                or (re.match(r"^ない$", e[7]) and re.match(r"助動詞", e[4]))
                or (re.match(r"^ぬ$", e[7]) and re.match(r"特殊・ヌ", e[5]))
            )
        ),
        # -- ます（助動詞）
        "masu": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^ます", e[7]) and re.match(r"助動詞", e[4])
        ),
        # -- ある（自立動詞）
        "aru": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^(ある|有る)$", e[7]) and re.match(r"動詞,自立", e[4])
        ),
        # -- なる（補助動詞）
        "naru": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^(なる|成る)$", e[7]) and re.match(r"動詞,非自立", e[4])
        ),
        # -- いく（補助動詞）
        "iku": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^(いく|行く)$", e[7]) and re.match(r"動詞,非自立", e[4])
        ),
        # -- いける（補助動詞）
        "ikeru": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^(いける|行ける)$", e[7]) and re.match(r"動詞,非自立", e[4])
        ),
        # -- て・で（接続助詞）
        "te": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^(て|で)$", e[7]) and re.match(r"助詞,接続助詞", e[4])
        ),
        # -- う（助動詞）
        "u": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^う$", e[7]) and re.match(r"助動詞", e[4])
        ),
        # -- だろ
        # -- でしょ
        "daro": tuple(
            JanomeLexEntry(*e)
            for e in sysdic
            if re.match(r"^(だ|です)$", e[7]) and re.match(r"未然形", e[6])
        )
    }

    # ------
    # generating intermediate morphemes
    # ------
    # -- ません（助動詞）
    morphemes_masen: typing.Tuple[JanomeLexEntry] = tuple(
        head._replace(
            surface = masu.surface + head.surface,
            left_id = masu.left_id,
            base_form = masu.base_form + head.base_form,
            reading = masu.reading + head.reading,
            phonetic = masu.phonetic + head.phonetic,
        )
        for masu in morphemes["masu"]
            if re.match(r"未然形", masu.infl_form)
                # -- ruling out 未然ウ接続 for ましょう
        for head in morphemes["nai_aux"]
            if re.match(r"^ん", head.surface)
    )

    morphemes_intermediate: typing.Dict[
        str, typing.Tuple[JanomeLexEntry]
    ] = {
        # -- ない・ありません（述語）
        "nai/arimasen": tuple(
            itertools.chain(
                # -- ない
                morphemes["nai_adj"],
                # -- ありません
                (
                    head._replace(
                        surface = aru.surface + head.surface,
                        left_id = aru.left_id,
                        base_form = aru.base_form + head.base_form,
                        reading = aru.reading + head.reading,
                        phonetic = aru.phonetic + head.phonetic,
                    )
                    for aru in morphemes["aru"]
                        if re.match(r"連用形", aru.infl_form)
                        # excluing テ形 such as in あって
                    for head in morphemes_masen
                )
            )
        ),
        # -- ならない・ならぬ・ならん・なりません
        "naranai/naranu/naran/narimasen": tuple(
            itertools.chain(
                # -- ならない・ぬ・ん
                (
                    head._replace(
                        surface = vb2.surface + head.surface,
                        left_id = vb2.left_id,
                        base_form = vb2.base_form + head.base_form,
                        reading = vb2.reading + head.reading,
                        phonetic = vb2.phonetic + head.phonetic,
                    )
                    for vb2 in morphemes["naru"]
                        if re.match(r"未然形", vb2.infl_form)
                        # excluding 未然ウ接続 such as in なろう
                    for head in morphemes["nai_aux"]
                ),
                # -- なりません
                (
                    head._replace(
                        surface = vb2.surface + head.surface,
                        left_id = vb2.left_id,
                        base_form = vb2.base_form + head.base_form,
                        reading = vb2.reading + "マセ" + head.reading,
                        phonetic = vb2.phonetic + "マセ" + head.phonetic,
                    )
                    for vb2 in morphemes["naru"]
                        if re.match(r"連用形", vb2.infl_form)
                        # excluding テ形 such as in なって
                    for head in morphemes_masen
                )
            )
        ),
        # -- いけない・いかぬ・いかん・いけません
        "ikenai/ikanu/ikan/ikemasen": tuple(
            itertools.chain(
                # -- いけない
                (
                    head._replace(
                        surface = vb2.surface + head.surface,
                        left_id = vb2.left_id,
                        base_form = vb2.base_form + head.base_form,
                        reading = vb2.reading + head.reading,
                        phonetic = vb2.phonetic + head.phonetic,
                    )
                    for vb2 in morphemes["ikeru"]
                        if re.match(r"未然形", vb2.infl_form)
                        # excluding 未然ウ接続 such as in ??行けよう
                    for head in morphemes["nai_aux"]
                        if re.match(r"^(ない|無い)$", head.base_form)
                ),
                # -- いかぬ・いかん
                (
                    head._replace(
                        surface = vb2.surface + head.surface,
                        left_id = vb2.left_id,
                        base_form = vb2.base_form + head.base_form,
                        reading = vb2.reading + head.reading,
                        phonetic = vb2.phonetic + head.phonetic,
                    )
                    for vb2 in morphemes["iku"]
                        if re.match(r"未然形", vb2.infl_form)
                        # excluding 未然ウ接続 such as in 行こう
                    for head in morphemes["nai_aux"]
                        if re.match(r"^(ぬ|ん)$", head.base_form)
                ),
                # -- いけません
                (
                    head._replace(
                        surface = vb2.surface + head.surface,
                        left_id = vb2.left_id,
                        base_form = vb2.base_form + head.base_form,
                        reading = vb2.reading + head.reading,
                        phonetic = vb2.phonetic + head.phonetic,
                    )
                    for vb2 in morphemes["ikeru"]
                        if re.match(r"連用形", vb2.infl_form)
                        # excluding テ形 such as in 行けて
                    for head in morphemes_masen
                ),
            )
        )
    }

    # ------
    # generating entries
    # ------
    # -- だろう・でしょう
    yield from (
        head._replace(
            surface = cop.surface + head.surface,
            left_id = cop.left_id,
            cost = head.cost - 10000,
            base_form = cop.base_form + head.base_form,
            reading = cop.reading + head.reading,
            phonetic = cop.phonetic + head.phonetic,
        )
        for cop in morphemes["daro"]
        for head in morphemes["u"]
    )

    # -- はずがない・ある・ありません
    yield from (
        head._replace(
            surface = (
                hazu.surface 
                + case["surface"] 
                + head.surface
            ),
            left_id = hazu.left_id,
            # right_id = ,
            cost = head.cost - 10000,
            #pos_major = ,
            #pos_minor1 = ,
            #pos_minor2 = ,
            #pos_minor3 = ,
            #infl_type = ,
            #infl_form =, 
            base_form = (
                hazu.base_form 
                + case["base_form"] 
                + head.base_form
            ), 
            reading = (
                hazu.reading 
                + case["reading"] 
                + head.reading
            ), 
            phonetic = (
                hazu.phonetic 
                + case["phonetic"] 
                + head.phonetic
            )
        )
        for hazu in morphemes["hazu"]
        for case in [
            {
                "surface": s,
                "base_form": s,
                "reading": r,
                "phonetic": p
            } for s, r, p in (
                ("が", "ガ", "ガ"), ("ガ", "ガ", "ガ"),
                ("は", "ハ", "ワ"), ("ハ", "ハ", "ワ"),
                ("も", "モ", "モ"), ("モ", "モ", "モ"),
                ("の", "ノ", "ノ"), ("ノ", "ノ", "ノ"),
            )
        ]
        for head in itertools.chain(
            morphemes_intermediate["nai/arimasen"],
            morphemes["aru"],
        )
    )

    # -- かもしれない
    yield from (
        head._replace(
            surface = (
                ka.surface 
                + case["surface"] 
                + head.surface
            ),
            left_id = ka.left_id,
            # right_id = ,
            cost = head.cost - 10000,
            #pos_major = ,
            #pos_minor1 = ,
            #pos_minor2 = ,
            #pos_minor3 = ,
            #infl_type = ,
            #infl_form =, 
            base_form = (
                ka.base_form 
                + case["base_form"] 
                + head.base_form
            ), 
            reading = (
                ka.reading 
                + case["reading"] 
                + head.reading
            ), 
            phonetic = (
                ka.phonetic 
                + case["phonetic"] 
                + head.phonetic
            )
        )
        for ka in morphemes["ka"]
        for case in [
            {
                "surface": s,
                "base_form": s,
                "reading": "モシレ",
                "phonetic": "モシレ"
            } for s in (
                "もしれ",
                "モシレ",
                "も知れ",
                "モ知レ"
            )
        ]
        for head in morphemes["nai_aux"]
    )

    # -- 「なければならない」系・「てはならない」系
    yield from (
        head._replace(
            surface = (
                nakeretewa.surface 
                + head.surface
            ),
            left_id = nakeretewa.left_id,
            # right_id = ,
            cost = head.cost - 10000,
            #pos_major = ,
            #pos_minor1 = ,
            #pos_minor2 = ,
            #pos_minor3 = ,
            #infl_type = ,
            #infl_form =, 
            base_form = (
                nakeretewa.base_form 
                + head.base_form
            ), 
            reading = (
                nakeretewa.reading 
                + head.reading
            ), 
            phonetic = (
                nakeretewa.phonetic 
                + head.phonetic
            )
        )
        for nakeretewa in itertools.chain(
            # なければ・なきゃ
            itertools.chain.from_iterable(
                _iter_nai_cond(nai) for nai in morphemes["nai_aux"]
            ),
            # ては
            (
                te._replace(
                    surface = te.surface + particle["surface"],
                    base_form = te.base_form + particle["base_form"],
                    reading = te.reading + particle["reading"],
                    phonetic = te.phonetic + particle["phonetic"],
                )
                for te in morphemes["te"]
                for particle in [
                    {
                        "surface": s,
                        "base_form": s,
                        "reading": r,
                        "phonetic": p
                    } for s, r, p in (
                        ("は", "ハ", "ワ"), ("ハ", "ハ", "ワ"),
                        ("も", "モ", "モ"), ("モ", "モ", "モ"),
                    )
                ]
            )
        )
        for head in itertools.chain(
            morphemes_intermediate["naranai/naranu/naran/narimasen"],
            morphemes_intermediate["ikenai/ikanu/ikan/ikemasen"],
        )
    )
# === END ===

def _iter_nai_cond(nai_entry: JanomeLexEntry) -> typing.Iterator[JanomeLexEntry]:
    """
    Iterate the forms with conditional particles 
        of a given lexical entry of negation (such as ない).

    - {なきゃ, なけりゃ}
    - {なけれ, ね}ば
    - {ない, ん}と
    - {なく, なくっ}{て, ては}

    Parameters
    ----------
    nai_entry : JanomeLexEntry
        An entry of negation markers.

    Yields
    -------
    nai_entry_conditional : JanomeLexEntry
        One of the conditional forms of the given entry.

    Examples
    --------
    >>> nai = JanomeLexEntry(
    ...     surface = "無い",
    ...     left_id = 1133,
    ...     right_id = 1144,
    ...     cost = -300,
    ...     part_of_speech = "",
    ...     infl_type = "",
    ...     infl_form = "基本",
    ...     base_form = "ない",
    ...     reading = "ナイ",
    ...     phonetic = "ナイ"
    ... )
    ... next(_iter_nai_cond(nai)).surface
    "無いと"
    """
    nai_entry_infl = nai_entry.infl_form

    if re.match(r"仮定", nai_entry_infl):
        if re.search(r"縮約", nai_entry_infl):
            # なきゃ, なけりゃ
            yield nai_entry
        else:
            # なけれ|ね - ば
            yield from (
                nai_entry._replace(
                    surface = (
                        nai_entry.surface 
                        + ba
                    ),
                    base_form = (
                        nai_entry.base_form 
                        + ba
                    ), 
                    reading = (
                        nai_entry.reading 
                        + "バ"
                    ), 
                    phonetic = (
                        nai_entry.phonetic 
                        + "バ"
                    )
                ) for ba in ("ば", "バ")
            )
        # === END IF ===
    elif re.match(r"^基本", nai_entry_infl):
        # ない, ん - と
        yield from (
            nai_entry._replace(
                surface = (
                    nai_entry.surface 
                    + to
                ),
                base_form = (
                    nai_entry.base_form 
                    + to
                ), 
                reading = (
                    nai_entry.reading 
                    + "ト"
                ), 
                phonetic = (
                    nai_entry.phonetic 
                    + "ト"
                )
            ) for to in ("と", "ト")
        )
    if re.match(r"連用テ接続", nai_entry_infl):
        # なく, なくっ - て. ては
        yield from (
            nai_entry._replace(
                surface = (
                    nai_entry.surface 
                    + te + wa["sb"]
                ),
                base_form = (
                    nai_entry.base_form 
                    + te + wa["sb"]
                ), 
                reading = (
                    nai_entry.reading 
                    + "テ" + wa["r"]
                ), 
                phonetic = (
                    nai_entry.phonetic 
                    + "テ" + wa["p"]
                )
            ) 
            for te in ("て", "テ")
            for wa in (
                {
                    "sb": "",
                    "r": "",
                    "p": "",
                },
                {
                    "sb": "は",
                    "r": "ハ",
                    "p": "ワ"
                },
                {
                    "sb": "ハ",
                    "r": "ハ",
                    "p": "ワ"
                },
            )
        )
    else:
        return
    # === END IF ===
# === END ===
