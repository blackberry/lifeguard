function tbl_row_filter(input,
                    table_id,
                    filter_data_class,
                    counted_chk_class,
                    counter_id_filtered,
                    counter_id_filtered_selected) {
    var filter_text = input.value;
    var num_filtered_selected = 0;
    var num_filtered = 0;
    $( "#" + table_id).find('tr').each(function (row_num, tr) {
        if (row_num == 0) return true;
        var row = $(this);
        row.find("td." + filter_data_class).each(function (td_num, td) {
            td = $(this);
            var text = td.text();
            if (filter_text == '' || text.indexOf(filter_text) != -1 ) {
                row.show()
            } else {
                num_filtered++;
                num_filtered_selected += row.find('input.'+counted_chk_class+'[type="checkbox"]:checked').length;
                row.hide();
            }
        });
    });
    $("#" + counter_id_filtered).html(num_filtered);
    $("#" + counter_id_filtered_selected).html(num_filtered_selected);
}

function counter_refresh(checkbox, counter_id_selected) {
    var selected_span = $("#" + counter_id_selected);
    num_selected = parseInt(selected_span.html());
    if (checkbox.checked) {
        selected_span.html(num_selected + 1);
    } else {
        selected_span.html(num_selected - 1);
    }
}

function tbl_toggle_checkboxes(master_checkbox, table_id) {
    $( "#" + table_id).find('tr').each(function (row_num, tr) {
        if (row_num == 0) return true;
        var row = $(this);
    });
}