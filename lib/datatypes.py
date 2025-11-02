# 用于存储可能存在的通用类型集
from typing import Union, TypeAlias

JsonDataType: TypeAlias = Union[
    dict[str, 'JsonDataType'], 
    list['JsonDataType'], 
    str, int, float, bool, None
]