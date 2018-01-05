# et

简单的文本模板渲染器。

## Example

```python
import et
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
print(et.render(tpl, i=1, logs=["tcp://10.123.23.14:5000", "tcp://10.123.23.15:5000"]))
```

OUTPUT:

```
    <!-- i: 1 -->
    <LogCategoryCount>2</LogCategoryCount>
    <LogCategory type="net">
        <Url>tcp://10.123.23.14:5000</Url>
    </LogCategory>
    <LogCategory type="net">
    </LogCategory>
    <!-- i: 1 -->
```

## 功能

- 渲染for ... in ... end
- 渲染if ... elif ... else ... end
- 渲染普通表达式
- 渲染时自动剔除纯表达式产生的空白行

## LICENSE

Do What The Fuck You Want To Public License
