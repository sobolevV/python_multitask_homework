from urllib import request, response
from urllib import error
from PIL import Image, ImageOps, UnidentifiedImageError
from io import BytesIO
import aiohttp, asyncio
global status_report

status_report = {
                "SUCCESS_DOWNLOADED": 0,
                "FAILED_DOWNLOADED": 0,
                "SUCCESS_POSTED": 0,
                "FAILED_POSTED": 0}


def get_images_from_url(url: str) -> list:
    images_list = None
    with request.urlopen(url) as resp:
        try:
            images_list = str(resp.read()).split("\\n")
        except error.HTTPError(url):
            print("Bad request")
    return images_list


async def image_handler(session, url: str, img_name: str, coroutine_index: int, queue):
    """
    Coroutine function, which download image by url + img_name.
    Data converts to pillow.Image and mirror by Y axes
        :param session: aiohttp.ClientSession object for downloading
        :param url: url with image data
        :param img_name: name of image for downloading
        :param coroutine_index: index of coroutine
        :param queue: asyncio.Queue object
        :return: None
    """
    data = None
    async with session.get(url+img_name) as resp:
        print(f"Coroutine № {coroutine_index} with response status {resp.status}")
        if resp.status == 200:
            try:
                data = await resp.read()
            except aiohttp.ClientResponseError:
                print("Response error", img_url)
        else:
            status_report["FAILED_DOWNLOADED"] += 1
            return
    try:
        img = Image.open(BytesIO(data))
    except Exception as e:
        print(e)
        return
    post_data = BytesIO(ImageOps.mirror(img).tobytes())
    status_report["SUCCESS_DOWNLOADED"] += 1
    await queue.put((post_data, img_name))


async def image_poster(url: str, queue, session, coroutine_index):
    """
    Post BytesIO data from q object to url
        :param url: url for posting data
        :param q: asyncio.Queue object
        :param session: aiohttp.ClientSession object for posting data
        :param coroutine_index: index of coroutine
        :return: None
    """
    post_data, img_name = await queue.get()
    try:
        resp = await session.post(url, data=post_data)
        print(f"Coroutine № {coroutine_index} posted Image {img_name} with status {resp.status}")
        status_report["SUCCESS_POSTED"] += 1
    except aiohttp.web.HTTPError() as e:
        print(e)
        status_report["FAILED_POSTEDI"] += 1
    queue.task_done()


async def main(main_url: str, img_names: list):
    q = asyncio.Queue()
    print("___GET DATA___")
    async with aiohttp.ClientSession() as session:
        coroutines = [asyncio.create_task(image_handler(session=session,
                                                        url=main_url,
                                                        img_name=image_name,
                                                        coroutine_index=index,
                                                        queue=q))
                      for index, image_name in enumerate(img_names)]
        await asyncio.gather(*coroutines)

    print("___POST DATA BACK___")
    async with aiohttp.ClientSession() as session_poster:
        coroutines_post = [image_poster(url=main_url,
                                        queue=q,
                                        session=session_poster,
                                        coroutine_index=index)
                           for index in range(q.qsize())]
        await asyncio.gather(*coroutines_post)

    await q.join()

if __name__ == '__main__':
    # url to get list of images
    img_url = "http://142.93.138.114/images/"
    # get list of images
    images = get_images_from_url(img_url)[:3]
    images[0] = images[0][2:]  # Почему-то 1-ая картинка оставляет b' в начале
    print(f"Got {len(images)} images")
    # run main coroutine
    if images:
        loop = asyncio.get_event_loop()
        asyncio.run(main(img_url, images), debug=True)
        print(status_report)
    else:
        print("List of images is empty ;(")


