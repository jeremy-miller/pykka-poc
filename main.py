import pprint
import socket

import pykka


class Calculator(pykka.ThreadingActor):
    def __init__(self):
        super().__init__()
        self.last_result = 0

    def add(self, a, b=None):
        if b is not None:
            self.last_result = a + b
        else:
            self.last_result += a
        return self.last_result

    def sub(self, a, b=None):
        if b is not None:
            self.last_result = a - b
        else:
            self.last_result -= a
        return self.last_result


class Playback:
    @staticmethod
    def play():
        return True


class TraversableActor(pykka.ThreadingActor):
    playback = pykka.traversable(Playback())


class Adder(pykka.ThreadingActor):
    def add_one(self, i):
        print(f"{self} is increasing {i}")
        return i + 1


# one actor referencing another
class Bookkeeper(pykka.ThreadingActor):
    def __init__(self, adder):
        super().__init__()
        self.adder = adder

    def count_to(self, target):
        i = 0
        while i < target:
            i = self.adder.add_one(i).get()
            print(f"{self} got {i} back")


# pool of actors
class Resolver(pykka.ThreadingActor):
    def resolve(self, ip):
        try:
            info = socket.gethostbyaddr(ip)
            print(f"Finished resolving {ip}")
            return info[0]
        except Exception:
            print(f"Failed resolving {ip}")
            return None


class Main:
    @staticmethod
    def run():
        calculator = Calculator.start().proxy()

        # using futures
        future = calculator.add(4)
        print(f"future version = {future.get()}")
        print(f"direct version = {calculator.last_result.get()}\n")

        calculator.add(7)
        calculator.sub(3)
        print(f"skipping blocking between calls = {calculator.last_result.get()}\n")

        traversable_actor = TraversableActor().start().proxy()
        play_success = traversable_actor.playback.play().get()
        print(f"play_success={play_success}\n")

        adder = Adder.start().proxy()
        bookkeeper = Bookkeeper.start(adder).proxy()
        bookkeeper.count_to(10).get()
        print()

        ips = [f"193.35.52.{i}" for i in range(1, 20)]
        pool_size = 10
        resolvers = [Resolver.start().proxy() for _ in range(pool_size)]
        hosts = []
        for i, ip in enumerate(ips):
            future = resolvers[i % len(resolvers)].resolve(ip)
            hosts.append(future)
        # gather results (blocking)
        ip_to_host = zip(ips, pykka.get_all(hosts))
        pprint.pprint(list(ip_to_host))

        pykka.ActorRegistry.stop_all()


if __name__ == "__main__":
    Main.run()
