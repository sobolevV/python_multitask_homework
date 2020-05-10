from urllib import request, response
from urllib import error
from PIL import Image, ImageOps, UnidentifiedImageError
from io import BytesIO
import aiohttp, asyncio
global status_report, sem, lock

# Report for check result
status_report = {
                "SUCCESS_DOWNLOADED": 0,
                "FAILED_DOWNLOADED": 0,
                "SUCCESS_POSTED": 0,
                "FAILED_POSTED": 0}
# 'Common data locker'
sem = asyncio.Semaphore(100)
lock = asyncio.Lock()

def get_images_from_url(url: str) -> list:
    images_list = None
    with request.urlopen(url) as resp:
        try:
            images_list = str(resp.read()).split("\\n")
        except error.HTTPError(url):
            print("Bad request")
    return images_list


async def image_handler(session, url: str, img_name: str, coroutine_index: int):
    """
    Coroutine function, which download image by url + img_name.
    Data converts to pillow.Image and mirror by Y axes
        :param session: aiohttp.ClientSession object for downloading
        :param url: url with image data
        :param img_name: name of image for downloading
        :param coroutine_index: index of coroutine
        :return: None
    """

    data = None
    async with session.get(url+img_name) as resp:
        print(f"Coroutine № {coroutine_index} with response status {resp.status}")
        # If response is successful
        if resp.status == 200:
            try:
                # read data from response
                data = await resp.read()
                status_report["SUCCESS_DOWNLOADED"] += 1
            except (aiohttp.ClientResponseError,
                    aiohttp.ClientError,
                    aiohttp.ClientOSError,
                    aiohttp.ServerTimeoutError,
                    asyncio.TimeoutError) as exc:
                print(f"Coroutine № {coroutine_index}: Response error", exc)
        else:
            status_report["FAILED_DOWNLOADED"] += 1
            return

    try:
        # Read bytes data to Image object
        img = Image.open(BytesIO(data))
    except Exception as exc:
        print(exc)
        return

    # Mirror Image object and convert it back to bytes
    post_data = BytesIO(ImageOps.mirror(img).tobytes())

    try:
        # Post data to server
        async with session.post(url, data=post_data) as resp_post:
            print(resp_post.status)
            print(f"Coroutine {coroutine_index} posted image {img_name} with status ", resp_post.status)
        status_report["SUCCESS_POSTED"] += 1
    except (aiohttp.ClientResponseError,
            aiohttp.ClientError,
            aiohttp.ClientOSError,
            aiohttp.ServerTimeoutError,
            asyncio.TimeoutError) as exc:
        print(f"Coroutine № {coroutine_index}: Post failed", exc)
        status_report["FAILED_POSTED"] += 1
        return



async def main(main_url: str, img_names: list):
    # Create connection
    async with aiohttp.ClientSession() as session:
        # Create coroutines with args
        coroutines = [image_handler(session=session,
                                    url=main_url,
                                    img_name=image_name,
                                    coroutine_index=index)
                      for index, image_name in enumerate(img_names)]
        # start all coroutines
        await asyncio.gather(*coroutines)


if __name__ == '__main__':
    # url to get list of images
    img_url = "http://142.93.138.114/images/"
    # get list of images
    images = get_images_from_url(img_url)
    images[0] = images[0][2:]  # Почему-то 1-ая картинка оставляет b' в начале
    print(f"Got {len(images)} images")
    # run main coroutine
    if images:
        loop = asyncio.get_event_loop()
        asyncio.run(main(img_url, images), debug=True)
        print(status_report)
    else:
        print("List of images is empty ;(")


