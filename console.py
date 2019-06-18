import sys
import tb as traceback

from browser import document as doc
from browser import window, alert, console

class Trace:

    def __init__(self):
        self.buf = ""

    def write(self, data):
        self.buf += str(data)

    def format(self):
        """Remove calls to function in this script from the traceback."""
        lines = self.buf.split("\n")
        stripped = [lines[0]]
        for i in range(1, len(lines), 2):
            if __file__ in lines[i]:
                continue
            stripped += lines[i: i+2]
        return "\n".join(stripped)


class Console:

    def __init__(self, element, namespace={}):
        self.element = element
        element.bind('keypress', self.keypress)
        element.bind('keydown', self.keydown)
        element.bind('click', self.cursorToEnd)
        element.focus()
        self.cursorToEnd()
        self.status = "main"
        self.current = 0
        self.history = []
        self.buffer = ""
        sys.stdout = self
        sys.stderr = self
        self.namespace = namespace

    def clear(self):
        self.buffer = ''
        self.element.value = ''

    def cursorToEnd(self, *args):
        pos = len(self.element.value)
        self.element.setSelectionRange(pos, pos)
        self.element.scrollTop = self.element.scrollHeight

    def keypress(self, event):
        if event.keyCode == 9:  # tab key
            event.preventDefault()
            self.element.value += "    "
        elif event.keyCode == 13:  # return
            src = self.element.value
            if self.status == "main":
                currentLine = src[src.rfind('>>>') + 4:]
            elif self.status == "3string":
                currentLine = src[src.rfind('>>>') + 4:]
                currentLine = currentLine.replace('\n... ', '\n')
            else:
                currentLine = src[src.rfind('...') + 4:]
            if self.status == 'main' and not currentLine.strip():
                self.element.value += '\n>>> '
                event.preventDefault()
                return
            self.element.value += '\n'
            self.history.append(currentLine)
            self.current = len(self.history)
            if self.status == "main" or self.status == "3string":
                try:
                    _ = self.namespace['_'] = eval(currentLine, self.namespace)
                    if _ is not None:
                        self.write(repr(_)+'\n')
                    self.write('>>> ')
                    self.status = "main"
                except IndentationError:
                    self.element.value += '... '
                    self.status = "block"
                except SyntaxError as msg:
                    if str(msg) == 'invalid syntax : triple string end not found' or \
                            str(msg).startswith('Unbalanced bracket'):
                        self.element.value += '... '
                        self.status = "3string"
                    elif str(msg) == 'eval() argument must be an expression':
                        try:
                            exec(currentLine, self.namespace)
                        except:
                            self.print_tb()
                        self.write('>>> ')
                        self.status = "main"
                    elif str(msg) == 'decorator expects function':
                        self.element.value += '... '
                        self.status = "block"
                    else:
                        self.syntax_error(msg.args)
                        self.element.value += '>>> '
                        self.status = "main"
                except:
                    # the full traceback includes the call to eval(); to
                    # remove it, it is stored in a buffer and the 2nd and 3rd
                    # lines are removed
                    self.print_tb()
                    self.element.value += '>>> '
                    self.status = "main"
            elif currentLine == "":  # end of block
                block = src[src.rfind('>>>') + 4:].splitlines()
                block = [block[0]] + [b[4:] for b in block[1:]]
                block_src = '\n'.join(block)
                # status must be set before executing code in globals()
                self.status = "main"
                try:
                    _ = exec(block_src, self.namespace)
                    if _ is not None:
                        print(repr(_))
                except:
                    self.print_tb()
                self.write('>>> ')
            else:
                self.element.value += '... '

            self.cursorToEnd()
            event.preventDefault()

    def keydown(self, event):
        if event.keyCode == 37:  # left arrow
            sel = self.get_col()
            if sel < 5:
                event.preventDefault()
                event.stopPropagation()
        elif event.keyCode == 36:  # line start
            pos = self.element.selectionStart
            col = self.get_col()
            self.element.setSelectionRange(pos - col + 4, pos - col + 4)
            event.preventDefault()
        elif event.keyCode == 38:  # up
            if self.current > 0:
                pos = self.element.selectionStart
                col = self.get_col()
                # remove current line
                self.element.value = self.element.value[:pos - col + 4]
                self.current -= 1
                self.element.value += self.history[self.current]
            event.preventDefault()
        elif event.keyCode == 40:  # down
            if self.current < len(self.history) - 1:
                pos = self.element.selectionStart
                col = self.get_col()
                # remove current line
                self.element.value = self.element.value[:pos - col + 4]
                self.current += 1
                self.element.value += self.history[self.current]
            event.preventDefault()
        elif event.keyCode == 8:  # backspace
            src = self.element.value
            lstart = src.rfind('\n')
            if (lstart == -1 and len(src) < 5) or (len(src) - lstart < 6):
                event.preventDefault()
                event.stopPropagation()
        elif event.ctrlKey and event.keyCode == 65: # ctrl+a
            src = self.element.value
            pos = self.element.selectionStart
            col = self.get_col()
            self.element.setSelectionRange(pos - col + 4, len(src))
            event.preventDefault()
        elif event.keyCode in [33, 34]: # page up, page down
            event.preventDefault()

    def get_col(self):
        # returns the column num of cursor
        sel = self.element.selectionStart
        lines = self.element.value.split('\n')
        for line in lines[:-1]:
            sel -= len(line) + 1
        return sel

    def print_tb(self):
        trace = Trace()
        traceback.print_exc(file=trace)
        self.write(trace.format())

    def prompt(self):
        if self.element.value and not self.element.value.endswith('\n'):
            self.write('\n')
        self.write(">>> ")
        self.element.focus()

    def syntax_error(self, args):
        info, filename, lineno, offset, line = args
        print(f"  File {filename}, line {lineno}")
        print("    " + line)
        print("    " + offset * " " + "^")
        print("SyntaxError:", info)

    def write(self, data):
        self.element.value += str(data)


def mark(element):
    Console(element)
