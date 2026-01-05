# Experience

## QObject绑定问题 - 于 2025.11.30 解决

考虑以下类：

```python
class Page(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wdg = QWidget()
        ...
```

请问，当Page的实例被deleteLater()并删除时，`self.wdg`是否会自动删除？

一般会认为，“会”。当Page的实例被删除时，`self.wdg.__del__`会被调用，`self.wdg`会被删除。

然而，实际上，`self.wdg`并不会被删除。调用`self.wdg.__del__`并不会顺带调用`self.wdg.deleteLater()`，因此`self.wdg`并不会被删除。

那如何让`self.wdg`在Page被删除时自动删除呢？

我们考虑将`self.wdg`绑定到Page自身，即：

```python
class Page(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wdg = QWidget(self)
        ...
```

这样，当Page的实例被删除时，`self.wdg`也会被删除。

无需担心`self.wdg`的父级问题。即便`self.wdg`在界面上绑定别的控件，都不会更改`self.wdg`的父级。

具体而言，`PySide`，更具体的，`Qt`，对象销毁是基于树的。当树根被删除时，整棵树都会被删除。因此，当Page的实例被删除时，`self.wdg`也会被删除。

同时，一个控件在绑定到布局时：

- 如果没设置父级，则父级自动为布局的父级。
- 如果设置了父级，则父级不变。

也就是说，绑定的父级优先级比布局父级更高，它能“显式”的改变删除顺序，使其符合预期。
