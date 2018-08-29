
let imageTimeout;
let IMAGE_SWITCH_INTERVAL_MS = 1000;
let FEED_REFRESH_INTERVAL_MS = 15000; 

function extractImage(images, post) {
    let id = post.id;
    let image_url = "/image/" + id;
    let img = new Image();
    img.src = image_url;
    img.id = "current-slide";
    images.push(img);
}

function extractFeed(posts, feed_processor) {
    let images = [];
    posts.forEach(function(post) {extractImage(images, post)});
    feed_processor(images);
}

function getFeed(feed_processor) {
    $.ajax({url: "/feed"})
        .then(function(posts) {extractFeed(posts, feed_processor)});
}

function setup() {
    function start_cycling_images(images) {
        cycleImages(0, images);
    }

    getFeed(start_cycling_images);
    // set up a timer to continuously reload the feed:
    setInterval(function() {getFeed(start_cycling_images)},
                FEED_REFRESH_INTERVAL_MS);

    $('#content').click(function() {openFullscreen(document.body)});
}

function cycleImages(current_image, images) {
    clearTimeout(imageTimeout);
    wrapped_index = current_image % images.length;
    let container_div = $('#content');
    container_div.html(images[wrapped_index]);
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


$(document).ready(setup);
