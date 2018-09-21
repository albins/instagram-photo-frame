import collections
import pickle


class RingBuffer(collections.deque):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def push(self, item):
        if len(self) == self.maxlen:
            expunged_value = self[0]
        else:
            expunged_value = None
        self.append(item)
        return expunged_value


def dict_without(d, *keys_to_drop):
    return {k: d[k] for k in d if k not in keys_to_drop}


def read_ringbuffer():
    with open("ringbuffer.pickle", "rb") as fp:
        ringbuffer = pickle.loads(fp.read())
        print("Loaded {} lines of ringbuffer".format(len(ringbuffer)))
        return ringbuffer


def read_or_create_ringbuffer(buffer_length):
    try:
        return read_ringbuffer()
    except FileNotFoundError:
        return RingBuffer(maxlen=buffer_length)
