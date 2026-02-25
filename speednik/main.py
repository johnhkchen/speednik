import pyxel


class App:
    def __init__(self):
        pyxel.init(256, 224, title="Speednik", fps=60)
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

    def draw(self):
        pyxel.cls(1)
        pyxel.text(112, 109, "Speednik", 7)


if __name__ == "__main__":
    App()
