function row_filter(filter_id, table_id, filter_data_class) {
    var filter_text = $("#"+filter_id).val()
    $( "#" + table_id).find('tr').each(function (row_num, tr) {
        var row = $( "#" + tr.id)
        row.find("td." + filter_data_class).each(function (td_num, td) {
            td = $("#" + td.id)
            var text = td.text()
            if (filter_text == '' || text.indexOf(filter_text) != -1 ) {
                row.show()
            } else {
                console.log("have to hide: " + text)
                row.hide()
            }
        });
    });
}