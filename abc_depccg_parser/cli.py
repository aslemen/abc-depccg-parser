import typing
import itertools
import sys
import io
import pathlib 

import click

from . import parser
from . import dic

# ======
# Commandline commands
# ======

# ------
# Root
# ------
@click.group()
def cmd_main():
    pass
# === END ===

@cmd_main.command(
    name = "parse"
)
@click.option(
    "--model", "-m",
    type = click.Path(
        exists = True,
        file_okay = False,
        dir_okay = True,
    ),
    #default = "/...",
    metavar = "<user_model>"
)
@click.option(
    "--batchsize", "-b", "batch_size",
    type = click.IntRange(min = 1, max = None),
    default = 32,
    metavar = "<batch_size>",
)
@click.option(
    "--tokenize/--no-tokenize", "-t/-nt", "is_to_tokenize",
    default = False
)
@click.option(
    "--output-format", "--format", "-f", "output_format",
    type = click.Choice(
        [
            "ABCT", 
            'auto', 
            'deriv', 
            'xml', 
            'conll', 
            'html', 
            'prolog', 
            'jigg_xml', 
            'ptb', 
            'json'
        ],
        case_sensitive = False
    ),
    default = "ABCT",
    metavar = "<output_format>"
)
def cmd_parse(
    model: pathlib.Path,
    batch_size: int,
    is_to_tokenize: bool,
    output_format: str
):
    parsed_trees, doc_tagged = parser.parse_doc(
        doc = sys.stdin, 
        is_to_tokenize = is_to_tokenize,
        batchsize = batch_size
    )

    if output_format.lower() == "abct":
        for i, (parsed, tokens) in enumerate(zip(parsed_trees, doc_tagged), 1):
            parser.dump_parsed_ABCT(parsed, tokens, i)
        # === END FOR ===
    else:
        parser.dump_batch_parsed_others(
            parsed_trees,
            doc_tagged,
            output_format = output_format,
            lang = "ja",
            stream = sys.stdout,
        )
    # === END IF ===
# === END ===

@cmd_main.command(
    name = "dic"
)
def cmd_dic():
    dic.dump_dic_as_csv(stream = sys.stdout)
# === END ===