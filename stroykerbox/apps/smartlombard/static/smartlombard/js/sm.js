function getPawnInfo(workplace, number) {
    let organization = 6045;

    $.ajax({
        url: 'https://online.smartlombard.ru/api/debt/get',
        type: 'POST',
        dataType: 'json',
        data: {
            organization: organization,
            workplace: workplace,
            number: number,
        }
    })
        .done(function (response) {
            if (response.error) {
                alert(response.error);
            } else {
                $('#pawn_number').text(response.pawn_number);
                $('#date').text(response.datetime);
                $('#buyout_price').text(response.buyout_price);
                $('#price').text(response.price);
                $('#goods').text(response.goods[0]);
                $('#result').show();

                $('#summ').text(response.summ);
            }
        })
        .fail(function () {

        });
}

function getInfo() {
    let number = $('#pawn_number').val();
    let workplace = $('#workplace').val();

    if (number != '') {
        getPawnInfo(workplace, number);
    }
}

$(document).ready(function () {


    $('.get-pawn').click(function(e){
        e.preventDefault();

        $.ajax(
            'https://online.smartlombard.ru/api/debt/get', {
                data: {
                    "number": $('#pawn_number').val(),
                    "organization": 6045,
                    "workplace": $('#workplace').val()
                },
                type: "POST",
                dataType: "json",
                complete: function (result) {
                    var data = JSON.parse(result.responseText);

                    if (data && data.summ) {
                        $('#prolongation_url').attr("href", data.online_prolongation_url);


                    } else {
                        if (data.error) {
                            alert(data.error);
                        }
                    }
                }
            }
        );
    });
});

