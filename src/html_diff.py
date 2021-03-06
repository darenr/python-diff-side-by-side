import io
import os
import sys
import difflib
import argparse
import pygments
import webbrowser
from pygments.lexers import guess_lexer_for_filename
from pygments.lexer import RegexLexer
from pygments.formatters import HtmlFormatter
from pygments.token import *

# Monokai is not quite right yet
PYGMENTS_STYLES = ["vs", "xcode"]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html class="no-js">

<head>
  <meta charset="utf-8">
  <title>
    %(html_title)s
  </title>
  <meta name="description" content="">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="mobile-web-app-capable" content="yes">
  <link rel="stylesheet" href="%(reset_css)s" type="text/css">
  <link rel="stylesheet" href="%(diff_css)s" type="text/css">
  <link class="syntaxdef" rel="stylesheet" href="%(pygments_css)s" type="text/css">
</head>

<body>
  <div id="maincontainer" class="%(page_width)s">
    <div id="leftcode" class="left-inner-shadow codebox divider-outside-bottom">
      <div class="codefiletab">
        %(from_file)s
      </div>
      <div class="printmargin">
        01234567890123456789012345678901234567890123456789012345678901234567890123456789
      </div>
      %(original_code)s
    </div>
    <div id="rightcode" class="left-inner-shadow codebox divider-outside-bottom">
      <div class="codefiletab">
        %(to_file)s
      </div>
      <div class="printmargin">
        01234567890123456789012345678901234567890123456789012345678901234567890123456789
      </div>
      %(modified_code)s
    </div>
  </div>
  <script src="%(diff_js)s" type="text/javascript"></script>
</body>

</html>
"""


class DefaultLexer(RegexLexer):
    """
    lex each line as a token.
    """

    name = 'Default'
    aliases = ['default']
    filenames = ['*']

    tokens = {
        'root': [
            (r'.*\n', Text),
        ]
    }


class DiffHtmlFormatter(HtmlFormatter):
    """
    Formats a single source file with pygments and adds diff highlights based on the
    diff details given.
    """
    isLeft = False
    diffs = None

    def __init__(self, isLeft, diffs, *args, **kwargs):
        self.isLeft = isLeft
        self.diffs = diffs
        super(DiffHtmlFormatter, self).__init__(*args, **kwargs)

    def wrap(self, source, outfile):
        return self._wrap_code(source)

    def getDiffLineNos(self):
        retlinenos = []
        for idx, ((left_no, left_line), (right_no, right_line), change) in enumerate(self.diffs):
            no = None
            if self.isLeft:
                if change:
                    if isinstance(left_no, int) and isinstance(right_no, int):
                        no = '<span class="lineno_q lineno_leftchange">' + \
                            str(left_no) + "</span>"
                    elif isinstance(left_no, int) and not isinstance(right_no, int):
                        no = '<span class="lineno_q lineno_leftdel">' + \
                            str(left_no) + "</span>"
                    elif not isinstance(left_no, int) and isinstance(right_no, int):
                        no = '<span class="lineno_q lineno_leftadd">  </span>'
                else:
                    no = '<span class="lineno_q">' + str(left_no) + "</span>"
            else:
                if change:
                    if isinstance(left_no, int) and isinstance(right_no, int):
                        no = '<span class="lineno_q lineno_rightchange">' + \
                            str(right_no) + "</span>"
                    elif isinstance(left_no, int) and not isinstance(right_no, int):
                        no = '<span class="lineno_q lineno_rightdel">  </span>'
                    elif not isinstance(left_no, int) and isinstance(right_no, int):
                        no = '<span class="lineno_q lineno_rightadd">' + \
                            str(right_no) + "</span>"
                else:
                    no = '<span class="lineno_q">' + str(right_no) + "</span>"

            retlinenos.append(no)

        return retlinenos

    def _wrap_code(self, source):
        source = list(source)
        yield 0, '<pre>'

        for idx, ((left_no, left_line), (right_no, right_line), change) in enumerate(self.diffs):
            # print idx, ((left_no, left_line),(right_no, right_line),change)
            try:
                if self.isLeft:
                    if change:
                        if isinstance(left_no, int) and isinstance(right_no, int) and left_no <= len(source):
                            i, t = source[left_no - 1]
                            t = '<span class="left_diff_change">' + t + "</span>"
                        elif isinstance(left_no, int) and not isinstance(right_no, int) and left_no <= len(source):
                            i, t = source[left_no - 1]
                            t = '<span class="left_diff_del">' + t + "</span>"
                        elif not isinstance(left_no, int) and isinstance(right_no, int):
                            i, t = 1, left_line
                            t = '<span class="left_diff_add">' + t + "</span>"
                        else:
                            raise
                    else:
                        if left_no <= len(source):
                            i, t = source[left_no - 1]
                        else:
                            i = 1
                            t = left_line
                else:
                    if change:
                        if isinstance(left_no, int) and isinstance(right_no, int) and right_no <= len(source):
                            i, t = source[right_no - 1]
                            t = '<span class="right_diff_change">' + t + "</span>"
                        elif isinstance(left_no, int) and not isinstance(right_no, int):
                            i, t = 1, right_line
                            t = '<span class="right_diff_del">' + t + "</span>"
                        elif not isinstance(left_no, int) and isinstance(right_no, int) and right_no <= len(source):
                            i, t = source[right_no - 1]
                            t = '<span class="right_diff_add">' + t + "</span>"
                        else:
                            raise
                    else:
                        if right_no <= len(source):
                            i, t = source[right_no - 1]
                        else:
                            i = 1
                            t = right_line
                yield i, t
            except:
                # print "WARNING! failed to enumerate diffs fully!"
                pass  # this is expected sometimes
        yield 0, '\n</pre>'

    def _wrap_tablelinenos(self, inner):
        dummyoutfile = io.StringIO()
        lncount = 0
        for t, line in inner:
            if t:
                lncount += 1

            # compatibility Python v2/v3
            if sys.version_info > (3, 0):
                dummyoutfile.write(line)
            else:
                dummyoutfile.write(unicode(line))

        fl = self.linenostart
        mw = len(str(lncount + fl - 1))
        sp = self.linenospecial
        st = self.linenostep
        la = self.lineanchors
        aln = self.anchorlinenos
        nocls = self.noclasses

        lines = []
        for i in self.getDiffLineNos():
            lines.append('%s' % (i,))

        ls = ''.join(lines)

        # in case you wonder about the seemingly redundant <div> here: since the
        # content in the other cell also is wrapped in a div, some browsers in
        # some configurations seem to mess up the formatting...
        if nocls:
            yield 0, ('<table class="%stable">' % self.cssclass +
                      '<tr><td><div class="linenodiv" '
                      'style="background-color: #f0f0f0; padding-right: 10px">'
                      '<pre style="line-height: 125%">' +
                      ls + '</pre></div></td><td class="code">')
        else:
            yield 0, ('<table class="%stable">' % self.cssclass +
                      '<tr><td class="linenos"><div class="linenodiv"><pre>' +
                      ls + '</pre></div></td><td class="code">')
        yield 0, dummyoutfile.getvalue()
        yield 0, '</td></tr></table>'


class Namespace:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class DiffCode(object):
    """
    Manages a pair of source files and generates a single html diff page comparing
    the contents.
    """
    pygments_css_file = "./assets/codeformats/%s.css"
    diff_css_file = "./assets/diff.css"
    reset_css_file = "./assets/reset.css"
    diff_js_file = "./assets/diff.js"
    reset_css_file = "./assets/reset.css"
    jqueryJsFile = "./assets/jquery-1.12.4.min.js"

    def __init__(self, fromfile, tofile, fromtxt=None, totxt=None, name=None):
        self.filename = name
        self.fromfile = fromfile
        if fromtxt == None:
            try:
                with io.open(fromfile) as f:
                    self.fromlines = f.readlines()
            except Exception as e:
                print("Problem reading file %s" % fromfile)
                print(e)
                sys.exit(1)
        else:
            self.fromlines = [n + "\n" for n in fromtxt.split("\n")]
        self.leftcode = "".join(self.fromlines)

        self.tofile = tofile
        if totxt == None:
            try:
                with io.open(tofile) as f:
                    self.tolines = f.readlines()
            except Exception as e:
                print("Problem reading file %s" % tofile)
                print(e)
                sys.exit(1)
        else:
            self.tolines = [n + "\n" for n in totxt.split("\n")]
        self.rightcode = "".join(self.tolines)

    def getDiffDetails(self, fromdesc='', todesc='', context=False, numlines=5, tabSize=2):
        # change tabs to spaces before it gets more difficult after we insert
        # markkup
        def expand_tabs(line):
            # hide real spaces
            line = line.replace(' ', '\0')
            # expand tabs into spaces
            line = line.expandtabs(tabSize)
            # replace spaces from expanded tabs back into tab characters
            # (we'll replace them with markup after we do differencing)
            line = line.replace(' ', '\t')
            return line.replace('\0', ' ').rstrip('\n')

        self.fromlines = [expand_tabs(line) for line in self.fromlines]
        self.tolines = [expand_tabs(line) for line in self.tolines]

        # create diffs iterator which generates side by side from/to data
        if context:
            context_lines = numlines
        else:
            context_lines = None

        diffs = difflib._mdiff(self.fromlines, self.tolines, context_lines,
                               linejunk=None, charjunk=difflib.IS_CHARACTER_JUNK)
        return list(diffs)

    def format(self, **kwargs):

        options = Namespace(**kwargs)


        if not 'from_file_title' in options.__dict__:
            options.__dict__['from_file_title'] = self.fromfile

        if not 'to_file_title' in options.__dict__:
            options.__dict__['to_file_title'] = self.tofile

        self.diffs = self.getDiffDetails(self.fromfile, self.tofile)

        fields = ((self.leftcode, True, self.fromfile),
                  (self.rightcode, False, self.tofile))

        codeContents = []
        for (code, isLeft, filename) in fields:

            inst = DiffHtmlFormatter(isLeft,
                                     self.diffs,
                                     nobackground=False,
                                     linenos=True,
                                     style=options.syntax_css)

            try:
                self.lexer = guess_lexer_for_filename(self.filename, code)

            except pygments.util.ClassNotFound:
                if options.verbose:
                    print("No Lexer Found! Using default...")

                self.lexer = DefaultLexer()

            formatted = pygments.highlight(code, self.lexer, inst)

            codeContents.append(formatted)

        answers = {
            "html_title":     self.filename,
            "reset_css":      self.reset_css_file,
            "pygments_css":   self.pygments_css_file % options.syntax_css,
            "diff_css":       self.diff_css_file,
            "reset_css":      self.reset_css_file,
            "page_title":     self.filename,
            "original_code":  codeContents[0].strip(),
            "modified_code":  codeContents[1].strip(),
            "from_file":      options.from_file_title,
            "to_file":        options.to_file_title,
            "diff_js":        self.diff_js_file,
            "page_width":     "page-80-width" if options.print_width else "page-full-width"
        }

        self.htmlContents = HTML_TEMPLATE % answers

        return self.htmlContents


if __name__ == '__main__':
    file1 = "/Users/drace/tmp/pyspark_1.py"
    file2 = "/Users/drace/tmp/pyspark_2.py"

    print(DiffCode(file1, file2, name=file2).format(
        syntax_css='vs',
        print_width=80,
        from_file_title = file1,
        to_file_title = file2
    ))
