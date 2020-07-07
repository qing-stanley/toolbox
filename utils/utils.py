import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager


def set_matplotlib_font():
    font_manager.FontProperties(fname="./src/font/sarasa-fixed-sc-regular.ttf").get_name()
    plt.rcParams["font.family"] = ["Sarasa Fixed SC"]
    return
