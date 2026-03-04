jQuery(document).ready(function($){
    var searchInput = $('.search_input'),
        searchBtn = searchInput.next('button');

    searchBtn.click(function() {
        var searchInputVal = $(this).prev('.search_input').val();
        if (searchInputVal) {
            var url = searchInput.data('search-url');
            window.location = url + '?q=' + searchInputVal;
        }
    });

    searchInput.keyup(function(event) {
        if (event.keyCode === 13) {
            searchBtn.click();
        }
    });


    if (screen.width > 767) {
        const resultBox = $('.header-search-results');
        let searchInput = $('.search_input'),
            searchUrl = searchInput.data('search-url'),
            searchMinChars = searchInput.data('min-chars');

        searchInput.on('focus keyup paste', function(e) {
            var input = $(this),
                minChars = this.dataset.minChars;
            if (input.val().length >= searchMinChars) {
                $.ajax({
                    type: 'get',
                    url: searchUrl,
                    data: input.serialize(),
                    dataType: 'html'
                }).done( function(result) {
                    if (result.replace(/\s/g,'').length > 0) {
                        resultBox.html(result);
                        resultBox.show();
                        $(document).mouseup(function (e){
                            if (!resultBox.is(e.target) && resultBox.has(e.target).length === 0) {
                                resultBox.hide();
                            }
                        });
                    } else {
                        resultBox.html('');
                        resultBox.hide();
                    }
                });
            } else {
                resultBox.hide().empty();
            }
        });

    }


});
