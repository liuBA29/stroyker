/**
 * Карусель 8march: мгновенная прокрутка по клику на стрелки, одна карточка «крупная».
 * Вызов: init8marchCarousel(wrapElement, options)
 * wrapElement — контейнер, внутри которого ищутся track, prev, next, cards по селекторам из options.
 */
function init8marchCarousel(wrapEl, options) {
  if (!wrapEl || typeof wrapEl.querySelector !== 'function') return;

  var opts = options || {};
  var trackSelector = opts.trackSelector || '.index-promo-8march__track';
  var prevSelector = opts.prevSelector || '.index-promo-8march__arrow--prev';
  var nextSelector = opts.nextSelector || '.index-promo-8march__arrow--next';
  var cardSelector = opts.cardSelector || '.index-promo-8march__card';
  var cardLargeClass = opts.cardLargeClass || 'index-promo-8march__card--large';
  var gap = opts.gap != null ? opts.gap : 20;
  var smallW = opts.smallW != null ? opts.smallW : 260;
  var largeW = opts.largeW != null ? opts.largeW : 377;

  function getSizes() {
    var w = window.innerWidth;
    var bp = opts.breakpoints;
    if (bp && bp.length) {
      for (var i = bp.length - 1; i >= 0; i--) {
        if (w >= bp[i].minWidth) {
          return {
            smallW: bp[i].smallW != null ? bp[i].smallW : smallW,
            largeW: bp[i].largeW != null ? bp[i].largeW : largeW,
            gap: bp[i].gap != null ? bp[i].gap : gap
          };
        }
      }
    }
    return { smallW: smallW, largeW: largeW, gap: gap };
  }

  var track = wrapEl.querySelector(trackSelector);
  var prev = wrapEl.querySelector(prevSelector);
  var next = wrapEl.querySelector(nextSelector);
  var cards = track ? track.querySelectorAll(cardSelector) : [];

  if (!track || !cards.length) return;

  /* На малом экране прокрутка на контейнере карусели (.index-promo-8march__carousel), иначе — на треке */
  function getScrollContainer() {
    var s = getSizes();
    if (s.largeW <= s.smallW && track.parentElement) return track.parentElement;
    return track;
  }

  function getScrollLeftForIndex(index) {
    if (index <= 0) return 0;
    var s = getSizes();
    if (s.largeW <= s.smallW) {
      /* Малый экран: все карточки одинаковые */
      return index * (s.smallW + s.gap);
    }
    /* Большой экран: первая карточка крупная (377px), при прокрутке следующая становится крупной.
       Смещения: 0 → 0; 1 → прошли карточку 0 (она уже 260 после ухода) = smallW+gap; 2 → + карточку 1 (377) = + largeW+gap; 3 → + smallW+gap; ... */
    var offset = s.smallW + s.gap; /* до начала карточки 1 */
    for (var i = 1; i < index; i++) {
      offset += (i % 2 === 1 ? s.largeW + s.gap : s.smallW + s.gap);
    }
    return offset;
  }

  function updateCardSizes() {
    if (!track || !cards.length) return;
    var s = getSizes();
    var deltaW = s.largeW - s.smallW;
    /* На малом экране (одинаковые карточки) — только сбрасываем стили, без анимации «крупной» карточки */
    if (deltaW <= 0) {
      for (var j = 0; j < cards.length; j++) {
        cards[j].classList.remove(cardLargeClass);
        cards[j].style.width = '';
        cards[j].style.minWidth = '';
        cards[j].style.flexBasis = '';
        cards[j].style.transition = '';
      }
      return;
    }
    var scrollLeft = getScrollContainer().scrollLeft;
    var maxScroll = getScrollLeftForIndex(cards.length - 1);
    var i = 0;
    var progress = 0;
    if (scrollLeft <= 0) {
      i = 0;
      progress = 0;
    } else if (scrollLeft >= maxScroll - 1) {
      i = cards.length - 1;
      progress = 1;
    } else {
      for (var k = 0; k < cards.length - 1; k++) {
        var from = getScrollLeftForIndex(k);
        var to = getScrollLeftForIndex(k + 1);
        if (scrollLeft >= from && scrollLeft < to) {
          i = k;
          progress = (scrollLeft - from) / (to - from);
          break;
        }
      }
    }
    for (var j = 0; j < cards.length; j++) {
      cards[j].classList.remove(cardLargeClass);
      cards[j].style.width = '';
      cards[j].style.minWidth = '';
      cards[j].style.flexBasis = '';
      cards[j].style.transition = '';
    }
    if (progress <= 0.002) {
      cards[i].classList.add(cardLargeClass);
      return;
    }
    if (progress >= 0.998 && i + 1 < cards.length) {
      cards[i + 1].classList.add(cardLargeClass);
      return;
    }
    var wLeft = Math.round(s.smallW + deltaW * (1 - progress));
    var wRight = Math.round(s.smallW + deltaW * progress);
    cards[i].style.transition = 'none';
    cards[i].style.width = wLeft + 'px';
    cards[i].style.minWidth = wLeft + 'px';
    cards[i].style.flexBasis = wLeft + 'px';
    if (i + 1 < cards.length) {
      cards[i + 1].style.transition = 'none';
      cards[i + 1].style.width = wRight + 'px';
      cards[i + 1].style.minWidth = wRight + 'px';
      cards[i + 1].style.flexBasis = wRight + 'px';
    }
  }

  function getCurrentIndex() {
    if (!track || !cards.length) return 0;
    var scrollLeft = getScrollContainer().scrollLeft;
    var s = getSizes();
    if (s.largeW <= s.smallW) {
      var step = s.smallW + s.gap;
      var idx = Math.floor((scrollLeft + 2) / step);
      return idx <= 0 ? 0 : (idx >= cards.length ? cards.length - 1 : idx);
    }
    /* Большой экран: находим индекс по тем же границам, что и getScrollLeftForIndex */
    if (scrollLeft <= 0) return 0;
    var offset = s.smallW + s.gap;
    if (scrollLeft < offset) return 1;
    for (var k = 2; k < cards.length; k++) {
      offset += (k % 2 === 1 ? s.largeW + s.gap : s.smallW + s.gap);
      if (scrollLeft < offset) return k;
    }
    return cards.length - 1;
  }

  function setLargeByIndex(index) {
    var s = getSizes();
    if (s.largeW <= s.smallW) return; /* на малом экране не переключаем «крупную» карточку */
    for (var j = 0; j < cards.length; j++) {
      cards[j].classList.toggle(cardLargeClass, j === index);
      cards[j].style.width = '';
      cards[j].style.minWidth = '';
      cards[j].style.flexBasis = '';
    }
  }

  function runUpdate() {
    if (isAnimating) return;
    requestAnimationFrame(updateCardSizes);
  }

  var isAnimating = false;

  function scrollToIndex(targetIndex) {
    if (targetIndex < 0 || targetIndex >= cards.length) return;
    isAnimating = true;
    getScrollContainer().scrollLeft = getScrollLeftForIndex(targetIndex);
    setLargeByIndex(targetIndex);
    isAnimating = false;
  }

  runUpdate();
  var scrollEl = getScrollContainer();
  scrollEl.addEventListener('scroll', runUpdate);
  window.addEventListener('resize', runUpdate);
  if (document.readyState !== 'complete') window.addEventListener('load', runUpdate);

  if (prev) prev.addEventListener('click', function() {
    scrollToIndex(Math.max(0, getCurrentIndex() - 1));
  });
  if (next) next.addEventListener('click', function() {
    scrollToIndex(Math.min(cards.length - 1, getCurrentIndex() + 1));
  });
}
