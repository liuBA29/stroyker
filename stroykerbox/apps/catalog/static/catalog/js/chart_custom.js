'use strict';

window.chartColors = {
    red: 'rgb(255, 99, 132)',
    blue: 'rgb(54, 162, 235)',
};

// function minY(chart_card_prices) {
//     var minValue = Math.min.apply(Math, chart_card_prices);
//     return minValue - minValue * 0.1
// }

function maxY(chart_prices) {
    var maxValue = Math.max.apply(Math, chart_prices);
    return maxValue + (maxValue * 0.1)
}

var config = {
    type: 'line',
    data: {
        labels: priceDates,
        datasets: [{
            label: 'Цена',
            backgroundColor: window.chartColors.red,
            borderColor: window.chartColors.red,
            data: prices,
            fill: false,
        }]
    },
    options: {
        responsive: true,
        title: {
            display: false,
        },
        tooltips: {
            mode: 'index',
            intersect: false,
        },
        hover: {
            mode: 'nearest',
            intersect: true
        },
        scales: {
            xAxes: [{
                display: true,
                scaleLabel: {
                    display: true,
                    labelString: label_period
                }
            }],
            yAxes: [{
                display: true,
                ticks: {
                    // suggestedMin: minY(card_prices),
                    suggestedMax: maxY(prices)
                },
                scaleLabel: {
                    display: true,
                    labelString: 'Цена, руб.'
                }
            }]
        }
    }
};

var ctx = document.getElementById('canvas').getContext('2d');
var chart = new Chart(ctx, config);

function addData(chart, data) {
    chart.data.labels = data.chart_price_dates;
    chart.data.datasets[0].data = data.chart_prices;
    chart.update();
}

function removeData(chart) {
    chart.data.labels.pop();
    chart.data.datasets.forEach((dataset) => {
        dataset.data.pop();
    });
    chart.update();
}

function updateConfig(chart, data) {
    chart.options.scales.xAxes[0].scaleLabel.labelString = data.label_period;
    // chart.options.scales.yAxes[0].ticks.suggestedMin = minY(data.chart_card_prices);
    chart.options.scales.yAxes[0].ticks.suggestedMax = maxY(data.chart_prices);
    chart.update();
}

// ajax запрос данных истории price и card_price для графика цен страницы товара
if (typeof ajaxChartPricesDataUrl !== 'undefined') {
    $('.price-chart__select').on('click', 'li', function() {
        var period = $(this).data('value');
        var product_id = $('#product_id_for_chart').attr('value').replace(/\s/g,'');
        $.post(ajaxChartPricesDataUrl,
            {'period': period, 'product_id': product_id}).done(
                function (data) {
                    removeData(chart);
                    updateConfig(chart, data);
                    addData(chart, data);
                });
        // event.preventDefault();
    });
}

