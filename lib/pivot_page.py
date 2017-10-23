def generate_pivot_page(title, data_rows, rows, cols):
    rows = ', '.join('"' + row + '"' for row in rows)
    cols = ', '.join('"' + col + '"' for col in cols)
    result = []
    result.append('''
<!DOCTYPE html>
<html>
    <head>
        <title>%s</title>

        <!-- external libs from cdnjs -->
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery/1.11.2/jquery.min.js"></script>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.11.4/jquery-ui.min.js"></script>

        <!-- PivotTable.js libs from ../dist -->
        <link rel="stylesheet" type="text/css" href="https://pivottable.js.org/dist/pivot.css">
        <script type="text/javascript" src="https://pivottable.js.org/dist/pivot.js"></script>
        <style>
            body {font-family: Verdana;}
        </style>

        <!-- optional: mobile support with jqueryui-touch-punch -->
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui-touch-punch/0.2.3/jquery.ui.touch-punch.min.js"></script>

    </head>
    <body>
        <script type="text/javascript">

    $(function(){
        $("#output").pivotUI(
            [
''' % title)
    for row in data_rows:
        result.append('  {')
        for field in row:
            field_value = row[field]
            field_value = str(field_value).replace('"','') if field_value else ""
            result.append('"%s": "%s", ' % (field, field_value))
        result.append('},\n')
    result.append('''
            ],
            {
                rows: [%s],
                cols: [%s],
            }
        );
     });
        </script>
        <h3>%s</h3>
        <div id="output" style="margin: 30px;"></div>

    </body>
</html>''' % (rows, cols, title))
    return ''.join(result)
