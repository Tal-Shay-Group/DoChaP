from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def plot_colortable(colors, title='', emptycols=0):
    cell_width = 212
    cell_height = 22
    swatch_width = 48
    margin = 12
    topmargin = 40

    colu = 4
    n = len(colors)
    ncols = colu - emptycols
    nrows = n // ncols + int(n % ncols > 0)

    width = cell_width * colu + 2 * margin
    height = cell_height * nrows + margin + topmargin
    dpi = 72

    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    fig.subplots_adjust(margin / width, margin / height,
                        (width - margin) / width, (height - topmargin) / height)
    ax.set_xlim(0, cell_width * colu)
    ax.set_ylim(cell_height * (nrows - 0.5), -cell_height / 2.)
    ax.yaxis.set_visible(False)
    ax.xaxis.set_visible(False)
    ax.set_axis_off()
    ax.set_title(title, fontsize=24, loc="left", pad=10)

    for i in range(len(colors)):
        row = i % nrows
        col = i // nrows
        y = row * cell_height

        swatch_start_x = cell_width * col
        text_pos_x = cell_width * col + swatch_width + 7

        ax.text(text_pos_x, y, colors[i], fontsize=14,
                horizontalalignment='left',
                verticalalignment='center')

        ax.add_patch(
            Rectangle(xy=(swatch_start_x, y - 9), width=swatch_width,
                      height=18, facecolor=colors[i], edgecolor='0.7')
        )

    return fig


colors = ["#f2a5c4", "#458dcc", "#aff2a5", "#cc8d45",
          "#ff0000", "#bf0000", "#ff5757", "#b37979", "#bf6341", "#d9a693", "#ff8800", "#b39879", "#ffcc00",
          "#b29b3d", "#ffefad", "#d6e600", "#aaff00", "#4cb33d", "#00ff66", "#00d991", "#8bccb6", "#00ffee",
          "#00a3cc", "#9cd7e6", "#0088ff", "#0044ff", "#a5a5f2", "#7c3db3", "#b800e6", "#f2a5ed", "#e64eb3",
          "#e5005c", ]

colors2 = ["#DACCFF", "#9B72FF", "#B627FC", "#DE3D3D", "#FF6262", "#f5b0cb", "#ffccd8",
           "#CD923C", "#FFBB8F", "#FD9900", "#ffb90f", "#ffd700", "#FFFC3B", "#FFF599",
           "#FFFED3", "#ccff00", "#20F876", "#63C37F", "#5BAF2F", "#2D79FF", "#00ccff",
           "#7BEAD2", "#beebe9"]

colors3 = ["#FF4A46", "#1BE177", "#00CCFF", "#A30059", "#FFB500", "#006FA6", "#4FC601", "#FFDBE5",
           "#D16100", "#00C2A0", "#A079BF", "#C0B9B2", "#CC0744", "#549E79", "#B79762", "#B903AA", "#00846F",
           "#FF90C9", "#0AA6D8",   "#F4ABAA", "#A3F3AB", "#00C6C8",
           "#EA8B66","#BEC459", "#AA5199",  "#0089A3", "#EEC3FF", "#8FB0FF",
           "#004D43", "#F4D749", "#997D87", "#3B5DFF", "#FF2F80",
           "#6B7900", "#FFAA92", "#A1C299",
           "#885578", "#B77B68", "#FAD09F", "#456D75", "#FF8A9A", "#0086ED", "#D157A0", "#00A6AA",
           "#B4A8BD", "#FF913F", "#636375", "#A3C8C9", "#00FECF", "#B05B6F", "#3B9700", "#C8A1A1",
           "#7900D7", "#8CD0FF", "#A77500", "#6367A9", "#6B002C", "#9B9700", "#D790FF", "#63FFAC",
           "#72418F", "#FFF69F", "#BC23FF",
           "#99ADC0", "#922329", "#C2FFED", "#CB7E98", "#A4E804", "#324E72", "#6A3A4C", "#83AB58",
           "#D1F7CE", "#004B28", "#C8D0F6", "#BF5650", "#66796D", "#FF1A59", "#8ADBB4", "#C895C5",
           "#FF6832", "#66E1D3", "#D0AC94", "#7ED379", "#7A7BFF", "#D68E01", "#78AFA1", "#FEB2C6",
           "#75797C", "#837393", "#943A4D", "#B5F4FF", "#D2DCD5", "#9556BD", "#6A714A", "#02525F",
           "#5EBCD1", "#3D4F44", "#02684E", "#962B75", "#8D8546", "#9695C5",
           "#E773CE", "#D86A78", "#3E89BE", "#CA834E", "#518A87", "#5B113C", "#55813B", "#00005F",
           "#A97399", "#4B8160", "#59738A", "#FF5DA7", "#F7C9BF", "#6B94AA", "#51A058", "#A45B02",
           "#E20027", "#E7AB63", "#4C6001", "#9C6966", "#64547B", "#006A66", "#0045D2",
           "#006C31", "#7C6571", "#9FB2A4", "#00D891", "#15A08A", "#BC65E9", "#C6DC99", "#671190",
           "#6B3A64", "#F5E1FF", "#FFA0F2", "#CCAA35", "#374527", "#8BB400", "#797868", "#C6005A",
           "#C86240", "#29607C", "#7D5A44", "#CCB87C", "#B88183", "#B5D6C3", "#A38469", "#9F94F0",
           "#A74571", "#B894A6", "#71BB8C", "#00B433", "#789EC9", "#E4FFFC", "#BCB1E5", "#008941",
           "#76912F", "#0060CD", "#D20096", "#494B5A", "#A88C85",  "#958A9F", "#BDC9D2", "#9FA064", "#BE4700", "#658188", "#83A485", "#47675D",
           "#DFFB71", "#868E7E", "#98D058", "#6C8F7D", "#D7BFC2", "#3C3E6E", "#D83D66", "#2F5D9B",
           "#6C5E46", "#D25B88", "#5B656C", "#00B57F", "#545C46", "#866097", "#365D25", "#252F99",
           "#674E60", "#FC009C", "#92896B"]
plot_colortable(colors3)
plt.show()
