let imageTimeout;

// Alla lets som du inte tänker mutera borde vara `const`.
const IMAGE_SWITCH_INTERVAL_MS = 1000;
const FEED_REFRESH_INTERVAL_MS = 15000; 

function extractImage(post) {
    const id = post.id;
    const image_url = "/image/" + id;
    const img = new Image(); // Bara själva referensen som är constant, inte properties
    img.src = image_url;
    img.id = "current-slide";
    
    // Det känns märkligt att pusha något till en parameter du får in.
    // Du borde returnera för att undvika mutation så mycket som möjligt
    //images.push(img);
    
    return img;
}

function extractFeed(posts) {
    let images = [];
    posts.forEach((post) => {
        images.push(extractImage(post));
    });
    
    // Behöver du verkligen skicka med feed_processor hela vägen, kan du inte
    // bara returnera och anropa cycleImages senare?
    // feed_processor(images);
    
    return images;
}

function getFeed() {
    // Här borde du kunna använda `fetch` istället, men spelar väl ingen större roll
    fetch("/feed")
        .then((posts) => {
            const images = extractFeed(posts);
            cycleImages(0, images);
        });
}

function setup() {
    /* function start_cycling_images(images) {
        cycleImages(0, images);
    }*/

    getFeed();
    // set up a timer to continuously reload the feed:
    setInterval(getFeed, FEED_REFRESH_INTERVAL_MS);

    $('#content').click(function() {openFullscreen(document.body)});
}

function cycleImages(current_image, images) {
    clearTimeout(imageTimeout);
    wrapped_index = current_image % images.length;
    const container_div = $('#content');
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
