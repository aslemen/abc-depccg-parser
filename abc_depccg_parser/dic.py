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

        return _gen_abc_dic(janome_sys_dic.entries.values())
    # === END IF ===
# === END ===

def _gen_abc_dic(
    sysdic: typing.Iterable[typing.Iterable[typing.Any]]
) -> typing.Set[JanomeLexEntry]:
    # ------
    # collecting heads
    # ------
    # -- はず（名詞，非自立）
    entries_hazu = [
        JanomeLexEntry(*e)
        for e in sysdic
        if re.match(r"^(はず|ハズ|筈)$", e[7]) and re.match(r"名詞,非自立", e[4])
    ]

    # -- か（終助詞）
    entries_ka = [
        JanomeLexEntry(*e)
        for e in sysdic
        if re.match(r"^か$", e[7])
    ]
    
    # -- ない（形容詞）
    entries_nai_adj = [
        JanomeLexEntry(*e) 
        for e in sysdic
        if re.match(r"^(ない|無い)$", e[7]) and re.match(r"形容詞", e[4])
    ]

    # -- ない（助動詞）
    # -- ん（助動詞）
#    entries_nai_aux = [
#        JanomeLexEntry(*e)
#        for e in sysdic
#        if (
#            re.match(r"ん", e[7]) 
#            or (re.match(r"^ない$", e[7]) and re.match(r"助動詞", e[4]))
#        )
#    ]

    # -- ない（助動詞）
    # -- ん（助動詞）
    # -- ぬ（否定助動詞）
    entries_nai_aux = [
        JanomeLexEntry(*e)
        for e in sysdic
        if (
            re.match(r"ん", e[7]) 
            or (re.match(r"^ない$", e[7]) and re.match(r"助動詞", e[4]))
#            or re.match(r"^ぬ$", e[7])
            or (re.match(r"^ぬ$", e[7]) and re.match(r"特殊・ヌ", e[5]))
        )
    ]


    # -- ある（自立動詞）
    entries_aru = [
        JanomeLexEntry(*e)
        for e in sysdic
        if re.match(r"^(ある|有る)$", e[7]) and re.match(r"動詞,自立", e[4])
    ]

    # -- なる・いける（補助動詞）
    entries_vb2 = [
        JanomeLexEntry(*e)
        for e in sysdic
        if re.match(r"^(いける|行ける|なる|成る)$", e[7]) and re.match(r"動詞,非自立", e[4])
    ]

    # -- て・で（接続助詞）
    entries_te = [
        JanomeLexEntry(*e)
        for e in sysdic
        if re.match(r"^(て|で)$", e[7]) and re.match(r"助詞,接続助詞", e[4])
    ]


    # -- う（助動詞）
    entries_u = [
        JanomeLexEntry(*e)
        for e in sysdic
        if e[7] == "う" and re.match(r"助動詞", e[4])
    ]

    # -- だろ
    # -- でしょ
    entries_darodesho = [
        JanomeLexEntry(*e)
        for e in sysdic
        if re.match(r"^(だ|です)$", e[7]) and re.match(r"未然形", e[6])
    ] 

    # -- ありません
    entries_arimasen = [
        head._replace(
            surface = aru.surface + masu + head.surface,
            left_id = aru.left_id,
            base_form = aru.base_form + masu + head.base_form,
            reading = aru.reading + "マセ" + head.reading,
            phonetic = aru.phonetic + "マセ" + head.phonetic,
        )
        for masu in ("ませ", "マセ")
        for aru in entries_aru
            if re.match(r"連用", aru.infl_form)
        for head in entries_nai_aux
            if re.match(r"^ん", head.surface)
    ]

    # -- なりません、いけません
#    entries_vb2masen = [
#        head._replace(
#            surface = vb2.surface + masu + head.surface,
#            left_id = vb2.left_id,
#            base_form = vb2.base_form + masu + head.base_form,
#            reading = vb2.reading + "マセ" + head.reading,
#            phonetic = vb2.phonetic + "マセ" + head.phonetic,
#        )
#        for masu in ("ませ", "マセ")
#        for vb2 in entries_vb2
#            if re.match(r"連用", vb2.infl_form)
#        for head in entries_nai_aux
#            if re.match(r"^ん|ぬ", head.surface)
#    ]

    # -- ません
    entries_masen = [
        head._replace(
            surface = masu + head.surface,
            left_id = "*",
            base_form = masu + head.base_form,
            reading = "マセ" + head.reading,
            phonetic = "マセ" + head.phonetic,
        )
        for masu in ("ませ", "マセ")
        for head in entries_nai_aux
            if re.match(r"^ん|ぬ", head.surface)       
    ]


    # ------
    # generating entries
    # ------
    res: typing.Set[JanomeLexEntry] = set()

    # -- だろう・でしょう
    res.update(
        head._replace(
            surface = cop.surface + head.surface,
            left_id = cop.left_id,
            cost = head.cost - 10000,
            base_form = cop.base_form + head.base_form,
            reading = cop.reading + head.reading,
            phonetic = cop.phonetic + head.phonetic,
        )
        for cop in entries_darodesho
        for head in entries_u
    )

    # -- はずがない・ある・ありません
    res.update(
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
        for hazu in entries_hazu
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
            entries_nai_adj, 
            entries_aru, entries_arimasen
        )
    )

    # -- かもしれない
    res.update(
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
        for ka in entries_ka
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
        for head in entries_nai_aux
    )

    # -- なければならない
    res.update(
        head._replace(
            surface = (
                nakere.surface 
                + case["surface"] 
                + head.surface
            ),
            left_id = nakere.left_id,
            # right_id = ,
            cost = head.cost - 10000,
            #pos_major = ,
            #pos_minor1 = ,
            #pos_minor2 = ,
            #pos_minor3 = ,
            #infl_type = ,
            #infl_form =, 
            base_form = (
                nakere.base_form 
                + case["base_form"] 
                + head.base_form
            ), 
            reading = (
                nakere.reading 
                + case["reading"] 
                + head.reading
            ), 
            phonetic = (
                nakere.phonetic 
                + case["phonetic"] 
                + head.phonetic
            )
        )
        for nakere in itertools.chain.from_iterable(
            _iter_nakya(nai) for nai in entries_nai_aux
        )
        for case in [
            {
                "surface": s,
                "base_form": s,
                "reading": rp,
                "phonetic": rp 
            } for s, rp in (
                ("なら", "ナラ"),
                ("ナラ", "ナラ"),
                ("成ら", "ナラ"),
                ("成ラ", "ナラ"),
                ("行ケ", "イケ"),
                ("行け", "イケ"),
                ("いけ", "イケ"),
                ("イケ", "イケ"),
            )
        ]
        for head in entries_nai_aux
    )
   
    # -- てはならない
    res.update(
        head._replace(
            surface = (
                te.surface 
                + particle["surface"] 
                + head.surface
            ),
            left_id = te.left_id,
            # right_id = ,
            cost = head.cost - 10000,
            #pos_major = ,
            #pos_minor1 = ,
            #pos_minor2 = ,
            #pos_minor3 = ,
            #infl_type = ,
            #infl_form =, 
            base_form = (
                te.base_form 
                + particle["base_form"] 
                + head.base_form
            ), 
            reading = (
                te.reading 
                + particle["reading"] 
                + head.reading
            ), 
            phonetic = (
                te.phonetic 
                + particle["phonetic"] 
                + head.phonetic
            )
        )
        for te in entries_te
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
        for head in itertools.chain.from_iterable(
            _iter_vb2(vb2) for vb2 in entries_vb2
    )

    return res
 
# === END ===

def _iter_nakya(nai_entry: JanomeLexEntry) -> typing.Iterator[JanomeLexEntry]:
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

def _iter_vb2(vb2_entry: JanomeLexEntry) -> typing.Iterator[JanomeLexEntry]:
    vb2_entry_infl = vb2_entry.infl_form

    if re.match(r"連用", vb2_entry_infl):
        # なりません
        yield from (
            vb2_entry._replace(
                surface = (
                    vb2_entry.surface 
                    + masen.surface
                ),
                base_form = (
                    vb2_entry.base_form 
                    + masen.base_form
                ), 
                reading = (
                    vb2_entry.reading 
                    + masen.reading
                ), 
                phonetic = (
                    vb2_entry.phonetic 
                    + masen.phonetic
                )
            ) for masen in entries_masen
        )
    elif re.match(r"^未然", vb2_entry_infl):
        # ならない
        yield from (
            vb2_entry._replace(
                surface = (
                    vb2_entry.surface 
                    + nai.surface
                ),
                base_form = (
                    vb2_entry.base_form 
                    + nai.base_form
                ), 
                reading = (
                    vb2_entry.reading 
                    + nai.reading
                ), 
                phonetic = (
                    vb2_entry.phonetic 
                    + nai.phonetic
                )
            ) for nai in entries_nai_aux
        )
    else:
        return
    # === END IF ===
# === END ===

