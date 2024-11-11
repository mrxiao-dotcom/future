import json


def echarts_line(title, list_data):
    option = {}

    option['title'] = {}
    option['title']['text'] = title

    option['tooltip'] = {}
    option['tooltip']['trigger'] = 'axis'

    option['grid'] = {}
    option['grid']['left'] = '3%'
    option['grid']['right'] = '4%'
    option['grid']['bottom'] = '3%'
    option['grid']['containLabel'] = True

    option['yAxis'] = {}
    option['yAxis']['type'] = 'value'

    legend = []
    x_axes = []
    series_map = {}
    for item in list_data:
        if legend.count(item['yname']) == 0:
            legend.append(item['yname'])
        if x_axes.count(item['xname']) == 0:
            x_axes.append(item['xname'])
        if series_map.get(item['yname']) is None:
            series_map[item['yname']] = {}
        series_map[item['yname']][item['xname']] = item['value']

    # print(json.dumps(seriesMap, ensure_ascii=False))
    option['legend'] = {}
    option['legend']['data'] = legend

    option['xAxis'] = {}
    option['xAxis']['type'] = 'category'
    option['xAxis']['boundaryGap'] = False
    option['xAxis']['data'] = x_axes

    series = []
    for y in legend:
        data = series_map.get(y)
        xd = []
        for x in x_axes:
            xd.append(data.get(x))
        tmp_data = {}
        tmp_data['name'] = y
        tmp_data['type'] = 'line'
        tmp_data['data'] = xd
        series.append(tmp_data)
    option['series'] = series
    return json.dumps(option, ensure_ascii=False)


# listData = [{'yname': 'yy', 'xname': 'xx1', 'value': '2'}, {'yname': 'yy', 'xname': 'xx2', 'value': '3'},
#             {'yname': 'yy', 'xname': 'xx3', 'value': '4'}, {'yname': 'yy', 'xname': 'xx4', 'value': '5'},
#             {'yname': 'yyaa', 'xname': 'xx1', 'value': '1'}, {'yname': 'yyaa', 'xname': 'xx2', 'value': '5'},
#             {'yname': 'yyaa', 'xname': 'xx3', 'value': '6'}, {'yname': 'yyaa', 'xname': 'xx4', 'value': '7'}]
# lineStr = echarts_line('测试标题', listData)
#
# print(lineStr)
