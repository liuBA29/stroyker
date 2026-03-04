document.addEventListener("DOMContentLoaded", function() {
    const currPath = window.location.href;
    const lkMenuItems = document.querySelectorAll('.lk-menu li');


    lkMenuItems.forEach(function (item) {
        if (currPath.indexOf(item.firstChild.href) == 0) {
            item.classList.add('current');
        }
    });

    const lkMenuItemsMobile = document.querySelectorAll('.mobile-menu-item');

    lkMenuItemsMobile.forEach(function (item) {
        if (currPath.indexOf(item.href) == 0) {
            item.classList.add('active');
        }
    });

    $('ul.accordion-lk a.opener').click(function () {
        $(this).parent().find("ul:first").slideToggle();
        $(this).parent().toggleClass('active');
        return false;
    });
});

// lc: user docs and orders in mobile mode
$('.mobile-doc-year-select').change(function () {
    var $this = $(this),
        tabgroup = '#' + $this.parents('.tabs-lk-mobile').data('tabgroup'),
        target = '#' + $this.val();

    $(tabgroup).children('div').hide();
    $(target).show();

});

// lc: user orders
$('.tabgroup > div').hide();
$('.tabgroup > div:first-of-type').show();
$('.tabs-lk a').click(function (e) {
    e.preventDefault();
    var $this = $(this),
        tabgroup = '#' + $this.parents('.tabs-lk').data('tabgroup'),
        others = $this.closest('li').siblings().children('a'),
        target = $this.attr('href');
    others.removeClass('active');
    $this.addClass('active');
    $(tabgroup).children('div').hide();
    $(target).show();

});
