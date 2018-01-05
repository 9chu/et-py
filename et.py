# -*- coding: utf-8 -*-
# et - 简单的文本模板渲染器
#   by chu <1871361697@qq.com> @ 2018.1
#
# Reference: https://www.willmcgugan.com/blog/tech/post/a-method-for-rendering-templates-with-python/

# --- 节点部分 ---


class Node:
    def __init__(self, parent):
        self.parent = parent
        self.nodes = []

    def render(self, context):
        pass


class ForNode(Node):
    def __init__(self, parent, identifier, expression):
        Node.__init__(self, parent)
        self.identifier = identifier
        self.expression = expression

    def render(self, context):
        result = eval(self.expression, globals(), context)
        origin = context[self.identifier] if self.identifier in context else None
        for i in result:
            context[self.identifier] = i
            yield iter(self.nodes)
        if origin:
            context[self.identifier] = origin


class IfNode(Node):
    def __init__(self, parent, expression):
        Node.__init__(self, parent)
        self.expression = expression
        self.true_branch = self.nodes

    def render(self, context):
        test = eval(self.expression, globals(), context)
        if test:
            yield iter(self.true_branch)


class IfElseNode(Node):
    def __init__(self, parent, if_node):  # extent from IfNode
        Node.__init__(self, parent)
        self.expression = if_node.expression
        self.true_branch = if_node.true_branch
        self.false_branch = self.nodes

    def render(self, context):
        test = eval(self.expression, globals(), context)
        if test:
            yield iter(self.true_branch)
        else:
            yield iter(self.false_branch)


class ExpressionNode(Node):
    def __init__(self, parent, expression):
        Node.__init__(self, parent)
        self.expression = expression

    def render(self, context):
        return eval(self.expression, globals(), context)


# --- 解析部分 ---


class ParseError(Exception):
    def __init__(self, line, row, desc):
        self._line = line
        self._row = row
        self._desc = desc

    def __str__(self):
        return '%d:%d: %s' % (self._line, self._row, self._desc)


class TextConsumer:
    def __init__(self, text):
        self._text = text
        self._len = len(text)
        self._pos = 0
        self._line = 1
        self._row = 0

    def get_pos(self):
        return self._pos

    def get_line(self):
        return self._line

    def get_row(self):
        return self._row

    def read(self):
        if self._pos >= self._len:
            return '\0'
        ch = self._text[self._pos]
        self._pos += 1
        self._row += 1
        if ch == '\n':
            self._line += 1
            self._row = 0
        return ch

    def peek(self, advance=0):
        if self._pos + advance >= self._len:
            return '\0'
        return self._text[self._pos + advance]

    def substr(self, begin, end):
        return self._text[begin:end]


class Parser:
    OUTER_TOKEN_LITERAL = 1
    OUTER_TOKEN_EXPRESS = 2

    RESERVED = ["and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except", "exec",
                "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "not", "or", "pass", "print",
                "raise", "return", "try", "while", "with", "yield"]

    def __init__(self, text):
        self._text = text
        self._consumer = TextConsumer(text)

    @staticmethod
    def _is_starting_by_new_line(text):
        for i in range(0, len(text)):
            ch = text[i:i + 1]
            if ch == '\n':
                return True
            elif not ch.isspace():
                break
        return False

    @staticmethod
    def _is_ending_by_new_line(text):
        for i in range(len(text) - 1, -1, -1):
            ch = text[i:i + 1]
            if ch == '\n':
                return True
            elif not ch.isspace():
                break
        return False

    @staticmethod
    def _trim_left_until_new_line(text):
        for i in range(0, len(text)):
            ch = text[i:i+1]
            if ch == '\n':
                return text[i+1:]
            elif not ch.isspace():
                break
        return text

    @staticmethod
    def _trim_right_until_new_line(text):
        for i in range(len(text) - 1, -1, -1):
            ch = text[i:i+1]
            if ch == '\n':
                return text[0:i+1]  # save right \n
            elif not ch.isspace():
                break
        return text

    @staticmethod
    def _parse_blank(consumer):
        while consumer.peek().isspace():  # 跳过所有空白
            consumer.read()

    @staticmethod
    def _parse_identifier(consumer):
        ch = consumer.peek()
        if not (ch.isalpha() or ch == '_'):
            return ""
        chars = [consumer.read()]  # ch
        ch = consumer.peek()
        while ch.isalnum() or ch == '_':
            chars.append(consumer.read())  # ch
            ch = consumer.peek()
        return "".join(chars)

    @staticmethod
    def _parse_inner(content, line, row):
        """内层解析函数

        考虑到表达式解析非常费力不讨好，这里采用偷懒方式进行。
        表达式全部交由python自行解决，匹配仅匹配开头，此外不处理注释（意味着不能在表达式中包含注释内容）。

        当满足 for <identifier> in <...> 时产生 for节点
        当满足 if <...> 时产生 if节点
        当满足 elif <...> 时产生 elif节点
        当满足 else 时产生 else节点
        当满足 end 时产生 end节点

        :param content: 内层内容
        :param line: 起始行
        :param row: 起始列
        :return: 节点名称, 表达式部分, 可选的Identifier
        """
        consumer = TextConsumer(content)
        Parser._parse_blank(consumer)
        operator = Parser._parse_identifier(consumer)
        identifier = None
        if operator == "for":
            Parser._parse_blank(consumer)
            identifier = Parser._parse_identifier(consumer)
            if identifier == "" or (identifier in Parser.RESERVED):
                raise ParseError(consumer.get_line() + line - 1,
                                 consumer.get_row() + row if consumer.get_line() == 1 else consumer.get_row(),
                                 "Identifier expected")
            Parser._parse_blank(consumer)
            if Parser._parse_identifier(consumer) != "in":
                raise ParseError(consumer.get_line() + line - 1,
                                 consumer.get_row() + row if consumer.get_line() == 1 else consumer.get_row(),
                                 "Keyword 'in' expected")
            Parser._parse_blank(consumer)
            expression = content[consumer.get_pos():]
            if expression == "":
                raise ParseError(consumer.get_line() + line - 1,
                                 consumer.get_row() + row if consumer.get_line() == 1 else consumer.get_row(),
                                 "Expression expected")
        elif operator == "if" or operator == "elif":
            Parser._parse_blank(consumer)
            expression = content[consumer.get_pos():]
            if expression == "":
                raise ParseError(consumer.get_line() + line - 1,
                                 consumer.get_row() + row if consumer.get_line() == 1 else consumer.get_row(),
                                 "Expression expected")
        elif operator == "end" or operator == "else":
            Parser._parse_blank(consumer)
            expression = content[consumer.get_pos():]
            if expression != '':
                raise ParseError(consumer.get_line() + line - 1,
                                 consumer.get_row() + row if consumer.get_line() == 1 else consumer.get_row(),
                                 "Unexpected content")
        else:
            operator = ""
            expression = content
        return operator, expression.strip(), identifier

    def _parse_outer(self):
        """外层解析函数

        将输入拆分成字符串(Literal)和表达式(Expression)两个组成。
        遇到'{%'开始解析Expression，在解析Expression时允许使用'%%'转义，即'%%'->'%'，这使得'%%>'->'%>'而不会结束表达式。

        :return: 类型, 内容, 起始行, 起始列
        """
        begin = self._consumer.get_pos()
        end = begin  # [begin, end)
        begin_line = self._consumer.get_line()
        begin_row = self._consumer.get_row()
        ch = self._consumer.peek()
        while ch != '\0':
            if ch == '{':
                ahead = self._consumer.peek(1)
                if ahead == '%':
                    if begin != end:
                        return Parser.OUTER_TOKEN_LITERAL, self._consumer.substr(begin, end), begin_line, begin_row
                    self._consumer.read()  # {
                    self._consumer.read()  # %
                    begin_line = self._consumer.get_line()
                    begin_row = self._consumer.get_row()
                    chars = []
                    while True:
                        ch = self._consumer.read()
                        if ch == '\0':
                            raise ParseError(self._consumer.get_line(), self._consumer.get_row(), "Unexpected eof")
                        elif ch == '%':
                            if self._consumer.peek() == '}':  # '%}'
                                self._consumer.read()
                                return Parser.OUTER_TOKEN_EXPRESS, "".join(chars), begin_line, begin_row
                            elif self._consumer.peek() == '%':  # '%%' -> '%'
                                self._consumer.read()
                        chars.append(ch)
            self._consumer.read()
            ch = self._consumer.peek()
            end = self._consumer.get_pos()
        return Parser.OUTER_TOKEN_LITERAL, self._consumer.substr(begin, end), begin_line, begin_row

    @staticmethod
    def _trim_empty_line(result):
        state = 0
        left = None  # 需要剔除右边的元素
        for i in range(0, len(result)):
            cur = result[i]
            p = result[i - 1] if i != 0 else None
            n = result[i + 1] if i != len(result) - 1 else None
            if state == 0:
                # 当前是表达式，且上一个是文本
                if cur[0] == Parser.OUTER_TOKEN_EXPRESS:
                    if p is None or (p[0] == Parser.OUTER_TOKEN_LITERAL and Parser._is_ending_by_new_line(p[1])):
                        left = i - 1 if p else None
                        state = 1
            if state == 1:
                if n is None or (n[0] == Parser.OUTER_TOKEN_LITERAL and Parser._is_starting_by_new_line(n[1])):
                    right = i + 1 if n else None
                    if left is not None:
                        result[left] = (result[left][0],
                                        Parser._trim_right_until_new_line(result[left][1]),
                                        result[left][2],
                                        result[left][3])
                    if right is not None:
                        result[right] = (result[right][0],
                                         Parser._trim_left_until_new_line(result[right][1]),
                                         result[right][2],
                                         result[right][3])
                    state = 0
                elif cur[0] != Parser.OUTER_TOKEN_EXPRESS:  # 行中有其他文本，不进行剔除
                    state = 0

    def process(self):
        root = []  # 根
        nodes = []  # 未闭合节点队列
        outer_results = []
        while True:  # 为了剔除空行，需要先解析完所有的根元素做预处理
            ret = self._parse_outer()
            if ret[0] == Parser.OUTER_TOKEN_LITERAL and ret[1] == "":  # EOF
                break
            outer_results.append(ret)
        Parser._trim_empty_line(outer_results)
        for i in outer_results:
            (t, content, line, row) = i
            back = None if len(nodes) == 0 else nodes[len(nodes) - 1]
            if t == Parser.OUTER_TOKEN_LITERAL:
                root.append(content) if back is None else back.nodes.append(content)
            else:
                assert t == Parser.OUTER_TOKEN_EXPRESS
                (operator, expression, identifier) = self._parse_inner(content, line, row)
                if operator == "for":
                    node = ForNode(back, identifier, expression)
                    root.append(node) if back is None else back.nodes.append(node)
                    nodes.append(node)
                elif operator == "if":
                    node = IfNode(back, expression)
                    root.append(node) if back is None else back.nodes.append(node)
                    nodes.append(node)
                elif operator == "else":
                    if not isinstance(back, IfNode):
                        raise ParseError(line, row, "Unexpected else branch")
                    node = IfElseNode(back.parent, back)
                    # 从root或者父节点中删除back
                    if back.parent is None:
                        assert root[len(root) - 1] == back
                        root.pop()
                        root.append(node)
                    else:
                        parent_nodes = back.parent.nodes
                        assert parent_nodes[len(parent_nodes) - 1] == back
                        parent_nodes.pop()
                        parent_nodes.append(node)
                    # 升级并取代
                    nodes.pop()
                    nodes.append(node)
                elif operator == "elif":
                    if not isinstance(back, IfNode):
                        raise ParseError(line, row, "Unexpected elif branch")
                    closed_else = IfElseNode(back.parent, back)
                    # 从root或者父节点中删除back
                    if back.parent is None:
                        assert root[len(root) - 1] == back
                        root.pop()
                        root.append(closed_else)
                    else:
                        parent_nodes = back.parent.nodes
                        assert parent_nodes[len(parent_nodes) - 1] == back
                        parent_nodes.pop()
                        parent_nodes.append(closed_else)
                    node = IfNode(closed_else, expression)
                    closed_else.nodes.append(node)
                    # 取代
                    nodes.pop()
                    nodes.append(node)
                elif operator == "end":
                    if back is None:
                        raise ParseError(line, row, "Unexpected block end")
                    nodes.pop()  # 完成一个节点
                else:
                    assert operator == ""
                    node = ExpressionNode(back, expression)
                    root.append(node) if back is None else back.nodes.append(node)
        if len(nodes) != 0:
            raise ParseError(self._consumer.get_line(), self._consumer.get_row(), "Unclosed block")
        return root


def _render(root, context):
    output = []
    stack = [iter(root)]
    while stack:
        node = stack.pop()
        if isinstance(node, basestring):
            output.append(node)
        elif isinstance(node, ExpressionNode):
            output.append(str(node.render(context)))
        elif isinstance(node, Node):
            stack.append(node.render(context))
        else:
            new_node = next(node, None)
            if new_node is not None:
                stack.append(node)
                stack.append(new_node)
    return "".join(output)


def render(template, **context):
    p = Parser(template)
    root = p.process()
    return _render(root, context)


if __name__ == "__main__":
    tpl = '''
        <!-- i: {% i %} -->
        <LogCategoryCount>{% len(logs) %}</LogCategoryCount>
        {% for i in range(0, len(logs)) %}
        <LogCategory type="net">
            {% if i == 0 %}
            <Url>{% logs[i] %}</Url>
            {% end %}
        </LogCategory>
        {% end %}
        <!-- i: {% i %} -->
    '''
    print(render(tpl, i=1, logs=["tcp://10.123.23.14:5000", "tcp://10.123.23.15:5000"]))
