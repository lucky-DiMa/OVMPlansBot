def sort_dict(dict_: dict, by: str, reverse: bool = False):
    sorted_by = reversed(sorted(dict_[by])) if reverse else sorted(dict_[by])
    result = {}
    for key in dict_.keys():
        result[key] = []
    for s in sorted_by:
        i = dict_[by].index(s)
        for key in dict_.keys():
            result[key].append(dict_[key].pop(i))
    return result
