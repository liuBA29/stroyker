$('.view-sort-item--1').on('click', function(){
    var cl =  $(this).parents('.catalog').find('.d-grid').attr("class").split(" ");
    var newcl =[];
    for(var i=0;i<cl.length;i++){
        r = cl[i].search(/grid-columns+/);
        if(r)newcl[newcl.length] = cl[i];
    }
    $(this).parents('.catalog').find('.d-grid').removeClass().addClass(newcl.join(" grid-columns-1 grid-columns-lg-3 grid-columns-xl-4 "));
})

$('.view-sort-item--2, .view-sort-item--3').on('click', function(){
    var cl =  $(this).parents('.catalog').find('.d-grid').attr("class").split(" ");
    var newcl =[];
    for(var i=0;i<cl.length;i++){
        r = cl[i].search(/grid-columns+/);
        if(r)newcl[newcl.length] = cl[i];
    }
    $(this).parents('.catalog').find('.d-grid').removeClass().addClass(newcl.join(" grid-columns-1 "));
})
