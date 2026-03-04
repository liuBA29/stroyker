window.addEventListener('load', () => {
    const addressList = document.querySelector('ul[data-role="address-location-select"]')

    if (addressList) {
        const observer = new MutationObserver(() => {
            const selectedItem = addressList.querySelector('li.selected')

            if (selectedItem) {
                const locationSlug = selectedItem.dataset.value
                if (locationSlug) {
                    window.location = `${window.location.pathname}?location=${locationSlug}`
                }
            }
        })

        observer.observe(addressList, {
            subtree: true,
            attributes: true
        })
    }

    ymaps.ready(init)
})

const YAMAP_CONTAINER_ID = 'yamap_addresses'
let myMap

function init() {
    const yamapContainer = document.getElementById(YAMAP_CONTAINER_ID)

    if (!yamapContainer) return

    const centerLatitude = parseFloat(yamapContainer.dataset.centerLatitude)
    const centerLongitude = parseFloat(yamapContainer.dataset.centerLongitude)
    const centerZoom = parseInt(yamapContainer.dataset.centerZoom, 10)

    myMap = new ymaps.Map(YAMAP_CONTAINER_ID, {
        center: [centerLatitude, centerLongitude],
        zoom: centerZoom
    }, {
        searchControlProvider: 'yandex#search'
    })

    addPoints(myMap, '.address-data')
}

function addPoints(map, selector) {
    document.querySelectorAll(selector).forEach((element) => {
        const latitude = parseFloat(element.dataset.latitude)
        const longitude = parseFloat(element.dataset.longitude)
        const balloonContent = element.dataset.balloonContent
        const hintContent = element.dataset.hintContent
        const iconPreset = element.dataset.iconPreset
        const glyphIconName = element.dataset.glyphIconName
        const glyphIconColor = element.dataset.glyphIconColor

        const geoObject = new ymaps.GeoObject({
            geometry: {
                type: 'Point',
                coordinates: [latitude, longitude]
            },
            properties: {
                balloonContent,
                hintContent
            }
        }, {
            preset: `islands#${iconPreset}`,
            iconGlyph: glyphIconName,
            iconGlyphColor: glyphIconColor,
            draggable: false
        })

        map.geoObjects.add(geoObject)
    })
}