#!/usr/bin/env python3
from UpdateAllFiles import updateTranslations
from check import performRender, performRenderLint
from IMAPLint import updateLintIMAPHandler
from VideoTranslations import updateVideoMap
from PolyglottIndexer import buildPolyglottIndex
from XLIFFReader import autotranslate_xliffs
from game.GameServer import run_game_server

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="Commands")
    # Generic argument
    parser.add_argument('-l', '--language', default="de", help='The language directory to use/extract (e.g. de, es)')

    updateTranslationsCmd = subparsers.add_parser('update-translations')
    updateTranslationsCmd.add_argument('-f', '--filter', nargs="*", action="append", help='Ignore file paths that do not contain this string, e.g. exercises or 2_high_priority. Can use multiple ones which are ANDed')
    updateTranslationsCmd.add_argument('-j', '--num-processes', default=16, type=int, help='Number of processes to use for parallel download')
    updateTranslationsCmd.add_argument('-m', '--force-filemap-update', action="store_true", help='Force updating the filemap')
    updateTranslationsCmd.add_argument('-a', '--all-languages', action="store_true", help='Download all languages')
    updateTranslationsCmd.add_argument('-p', '--po', action="store_true", help='Download as PO instead of XLIFF')
    updateTranslationsCmd.set_defaults(func=updateTranslations)

    updateLint = subparsers.add_parser('update-lint')
    updateLint.set_defaults(func=updateLintIMAPHandler)

    autotranslate = subparsers.add_parser('autotranslate')
    autotranslate.add_argument('-j', '--num-processes', default=16, type=int, help='Number of threads to use for parallel processing')
    autotranslate.add_argument('-u', '--upload', action="store_true", help='Upload to Crowdin')
    autotranslate.add_argument('-a', '--approve', action="store_true", help='For --upload, auto-approve the strings')
    autotranslate.add_argument('-f', '--filter', nargs="*", action="append", help='Ignore file paths that do not contain this string, e.g. exercises or 2_high_priority. Can use multiple ones which are ANDed')
    autotranslate.add_argument('-i', '--index', action="store_true", help='Recognize and export patterns of different types')
    autotranslate.add_argument('-o', '--overwrite', action="store_true", help='Export suggestions where there is an existing (but not approved) suggestion')
    autotranslate.add_argument('--only-approved', action="store_true", help='When indexing, only export patterns that have approved translations')
    autotranslate.add_argument('--index-ignore-translated', action="store_true", help='Ignore fully translated patterns')
    autotranslate.add_argument('--full-auto', action="store_true", help='Full-auto translation. USE SPARINGLY')
    autotranslate.add_argument('-l','--limit', type=int, default=1000000000, help='Number of string to translate using full auto mode')
    autotranslate.add_argument('--update-index-source', action="store_true", help='Update crowdin ka-babelfish source file for the index.')
    autotranslate.add_argument('--update-index', action="store_true", help='Update crowdin ka-babelfish autotranslation')
    autotranslate.add_argument('-p', '--patterns', action="store_true", help='Translate patterns')
    autotranslate.add_argument('-n', '--name-autotranslate', action="store_true", help='Auto-translate simple name patterns')
    autotranslate.set_defaults(func=autotranslate_xliffs)

    renderLint = subparsers.add_parser('update-video-translations')
    renderLint.set_defaults(func=updateVideoMap)

    gameServer = subparsers.add_parser('game-server')
    gameServer.add_argument('file', help='The file to read')
    gameServer.set_defaults(func=run_game_server)

    render = subparsers.add_parser('render')
    render.add_argument('-j', '--num-processes', default=2, type=int, help='Number of threads to use for parallel processing')
    render.add_argument('-d', '--download', action='store_true', help='Download or update the directory')
    render.add_argument('-f', '--filter', nargs="*", action="append", help='Ignore file paths that do not contain this string, e.g. exercises or 2_high_priority. Can use multiple ones which are ANDed')
    render.add_argument('--only-lint', action='store_true', help='Only render the lint hierarchy')
    render.add_argument('--no-lint', action='store_true', help='Do not render the lint hierarchy')
    render.add_argument('outdir', nargs='?', default=None, help='The output directory to use (default: output-<lang>)')
    render.set_defaults(func=performRender)

    index = subparsers.add_parser('index')
    index.add_argument('-t', '--table', type=int, default=1, help='Table offset (where to store the data in YakDB. 1 => production setup)')
    index.set_defaults(func=buildPolyglottIndex)

    args = parser.parse_args()

    # Call args.func, but do not catch AttributeError inside args.func()
    try:
        args.func
        err = False
    except AttributeError:
        parser.print_help()
        err = True
    if not err:
        args.func(args)
