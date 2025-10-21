import matplotlib.pyplot as plt

def plot_shares(df):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(df["operator"], df["s_star"])
    ax.set_ylabel("optimal share s*")
    ax.set_xlabel("operator")
    ax.set_title("Optimal stake shares (normalized)")
    fig.tight_layout()
    plt.show()
