let imageTimeout;

const IMAGE_SWITCH_INTERVAL_MS = 10000;
const FEED_REFRESH_INTERVAL_MS = 600000; 
const DOCUMENT_REFRESH_INTERVAL_MS = 4 * 60 * 60 * 1000;

function extractImage(post) {
    const id = post.id;
    const image_url = "/image/" + id;
    const img = new Image();
    img.src = image_url;
    img.id = "current-slide";
    return img;
}

function getFeed() {
    fetch("/feed")
        .then((response) => {return response.json()})
        .then((posts) => {
            cycleImages(0, posts.map(post => extractImage(post)));
        });
}

function setup() {
    getFeed();
    // set up a timer to continuously reload the feed:
    setInterval(getFeed, FEED_REFRESH_INTERVAL_MS);

    setInterval(() => {location.reload(true)},
                DOCUMENT_REFRESH_INTERVAL_MS);

    document.getElementById("content")
        .onclick = () => {openFullscreen(document.body)};
}

function cycleImages(current_image, images) {
    clearTimeout(imageTimeout);
    wrapped_index = current_image % images.length;
    const container_div = document.getElementById("content");
    if(container_div.firstChild) {
        container_div.replaceChild(images[wrapped_index],
                                   container_div.firstChild)
    } else {
        container_div.appendChild(images[wrapped_index]);
    }

    imageTimeout = setTimeout(function()
                              {cycleImages(current_image + 1, images)},
                              IMAGE_SWITCH_INTERVAL_MS);
}


function openFullscreen(elem) {
    console.log("Attempting full screen");
    if (elem.requestFullscreen) {
        elem.requestFullscreen();
    } else if (elem.mozRequestFullScreen) { /* Firefox */
        elem.mozRequestFullScreen();
    } else if (elem.webkitRequestFullscreen) { /* Chrome, Safari and Opera */
        elem.webkitRequestFullscreen();
    } else if (elem.msRequestFullscreen) { /* IE/Edge */
        elem.msRequestFullscreen();
    }
}

document.addEventListener("DOMContentLoaded", setup);

