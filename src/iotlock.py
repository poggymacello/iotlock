# iotlock.py - simulasi & analisis serangan ddos pada jaringan iot
# versi 1.0.0 (beta)
#
# cara pakai: tinggal jalanin aja file ini pake python3
# python3 src/iotlock.py
#
# requirements:
# - networkx
# - numpy
# - matplotlib
# - pillow

import os
import matplotlib
# set backend dulu sebelum import pyplot
matplotlib.use('Agg')  # backend yang cocok buat web

import networkx as nx  # buat bikin & analisis graf
import numpy as np    # buat perhitungan numerik
import matplotlib.pyplot as plt  # buat visualisasi
import matplotlib.animation as animation  # buat bikin animasi
import random  # buat generate nilai random
from typing import Dict, List, Tuple  # buat type hinting

# notes: algoritma kruskal dipake buat memastikan konektivitas optimal 
# dengan kompleksitas o(e log v) - referensi: kruskal, 1956

# fungsi buat bikin jaringan iot dan pohon spanning minimum
def bangun_jaringan(jumlah_node: int = 20) -> Tuple[nx.Graph, nx.Graph]:
    # bikin graf kosong dulu
    graf_iot = nx.Graph()
    
    # tambah node ke graf (0 sampai jumlah_node-1)
    graf_iot.add_nodes_from(range(jumlah_node))
    
    # tambah edge random dengan bobot antara 1-10
    # ini buat simulasi latensi antar perangkat iot
    for i in range(jumlah_node):
        for j in range(i + 1, jumlah_node):
            if random.random() < 0.3:  # 30% chance buat bikin edge
                graf_iot.add_edge(i, j, weight=random.randint(1, 10))
    
    # bikin minimum spanning tree pake algoritma kruskal
    # ini buat dapetin jalur optimal antar node
    pohon_minimum = nx.minimum_spanning_tree(graf_iot)
    
    return graf_iot, pohon_minimum

# notes: distribusi poisson dipake buat simulasi pola serangan ddos
# berdasarkan analisis traffic jaringan iot di dunia nyata

def simulasi_ddos(pohon_minimum: nx.Graph, maks_timestep: int = 10) -> List[Dict[int, str]]:
    jumlah_node = pohon_minimum.number_of_nodes()
    status_node = []
    
    # simulasi untuk setiap timestep
    for timestep in range(maks_timestep):
        status_saat_ini = {}
        
        # generate jumlah paket untuk setiap node
        for node in range(jumlah_node):
            # tingkatkan intensitas serangan seiring waktu
            lambda_serangan = 5 + (timestep * 2)  # makin lama makin intens
            
            # pake distribusi poisson buat simulasi serangan
            jumlah_paket = np.random.poisson(lam=lambda_serangan)
            
            # node gagal kalo:
            # - kena lebih dari 15 paket, atau
            # - tetangga-tetangganya banyak yang gagal (efek domino)
            tetangga = list(pohon_minimum.neighbors(node))
            tetangga_gagal = sum(1 for t in tetangga if t in status_saat_ini 
                               and status_saat_ini[t] == "gagal")
            
            gagal = (jumlah_paket > 15) or (tetangga_gagal >= len(tetangga) / 2)
            status_saat_ini[node] = "gagal" if gagal else "normal"
        
        status_node.append(status_saat_ini)
    
    return status_node

# notes: betweenness centrality dipake buat identifikasi node 
# yang paling kritis dalam jaringan - penting buat mitigasi

# fungsi buat analisis dampak serangan
def analisis_dampak(pohon_minimum: nx.Graph, status_ddos: List[Dict[int, str]]) -> Dict[int, float]:
    # hitung betweenness centrality
    centrality = nx.betweenness_centrality(pohon_minimum)
    
    # hitung berapa kali tiap node gagal
    jumlah_gagal = {node: sum(1 for status in status_ddos if status[node] == "gagal")
                    for node in pohon_minimum.nodes()}
    
    # hitung skor dampak (centrality * jumlah kegagalan)
    skor_dampak = {node: centrality[node] * jumlah_gagal[node]
                   for node in pohon_minimum.nodes()}
    
    return skor_dampak

# fungsi buat bikin animasi serangan
# tips: kalo animasi keliatannya kecepetan, bisa ubah interval di bawah
def animasi_serangan(pohon_minimum: nx.Graph, status_ddos: List[Dict[int, str]]) -> animation.FuncAnimation:
    # bikin figure dengan 2 subplot (graf dan progress bar)
    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(2, 1, height_ratios=[6, 1], hspace=0.3)
    ax_graph = fig.add_subplot(gs[0])
    ax_progress = fig.add_subplot(gs[1])
    
    plt.style.use('ggplot')  # pake style yang lebih modern
    
    # bikin layout yang lebih rapi dan konsisten
    pos = nx.spring_layout(pohon_minimum, k=1, iterations=50)
    
    def update(frame):
        # clear kedua axes
        ax_graph.clear()
        ax_progress.clear()
        
        status = status_ddos[frame]
        
        # hitung statistik
        total_nodes = len(pohon_minimum.nodes())
        gagal_nodes = sum(1 for n in status if status[n] == "gagal")
        persen_gagal = (gagal_nodes / total_nodes) * 100
        
        # hitung rata-rata latensi
        latensi = [d['weight'] for (u, v, d) in pohon_minimum.edges(data=True)]
        rata_latensi = sum(latensi) / len(latensi)
        
        # tentuin warna dan ukuran node berdasarkan status
        warna_node = []
        ukuran_node = []
        for node in pohon_minimum.nodes():
            if status[node] == "gagal":
                warna_node.append('#ff4444')  # merah untuk node gagal
                ukuran_node.append(800)  # node gagal lebih besar
            else:
                warna_node.append('#44ff44')  # hijau untuk node normal
                ukuran_node.append(500)
        
        # gambar grid background
        ax_graph.grid(True, linestyle='--', alpha=0.7)
        
        # gambar edges dengan warna berdasarkan weight
        edge_weights = [d['weight'] for (u, v, d) in pohon_minimum.edges(data=True)]
        nx.draw_networkx_edges(pohon_minimum, pos, 
                             edge_color='gray',
                             width=[w/3 for w in edge_weights],
                             alpha=0.3, ax=ax_graph)
        
        # gambar nodes
        nx.draw_networkx_nodes(pohon_minimum, pos, 
                             node_color=warna_node,
                             node_size=ukuran_node,
                             ax=ax_graph)
        
        # tambah label node
        nx.draw_networkx_labels(pohon_minimum, pos, font_size=8,
                              font_weight='bold', ax=ax_graph)
        
        # tambah label edge (weight/latensi)
        edge_labels = nx.get_edge_attributes(pohon_minimum, 'weight')
        nx.draw_networkx_edge_labels(pohon_minimum, pos,
                                   edge_labels=edge_labels,
                                   font_size=6)
        
        # bikin legend untuk graf
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#44ff44', label='Node Normal'),
            Patch(facecolor='#ff4444', label='Node Gagal')
        ]
        ax_graph.legend(handles=legend_elements, loc='upper right')
        
        # tambah info status yang lebih lengkap
        waktu = frame * 0.5  # anggap tiap frame = 0.5 detik
        ax_graph.set_title("simulasi serangan ddos\n" +
                        f"waktu: {waktu:.1f} detik\n" +
                        f"status: {gagal_nodes} dari {total_nodes} node gagal ({persen_gagal:.1f}%)\n" +
                        f"rata-rata latensi: {rata_latensi:.1f} ms")
        
        # gambar progress bar
        progress = (frame + 1) / len(status_ddos)
        ax_progress.barh(0, progress * 100, color='#2196f3', alpha=0.8)
        ax_progress.barh(0, 100, color='gray', alpha=0.2)
        ax_progress.set_xlim(0, 100)
        ax_progress.set_ylim(-0.5, 0.5)
        ax_progress.set_xlabel(f'Progress: {progress*100:.0f}%')
        ax_progress.set_yticks([])
    
    # bikin animasi (interval=500 artinya 0.5 detik per frame)
    ani = animation.FuncAnimation(fig, update, frames=len(status_ddos),
                                interval=500, repeat=True, cache_frame_data=False)
    return ani

def utama():
    try:
        # set style plot yang keren
        plt.style.use('ggplot')  # pake style built-in matplotlib
        # ini buat clear screen dulu biar rapi
        print("\n" * 2)
        print("=" * 50)
        print("simulasi keamanan jaringan iot".center(50))
        print("=" * 50)
        print()
        
        # bangun jaringan iot
        print("[+] membuat jaringan iot...")
        graf_iot, pohon_minimum = bangun_jaringan()
        
        # simulasi serangan ddos
        print("[+] mensimulasikan serangan ddos...")
        status_ddos = simulasi_ddos(pohon_minimum)
        
        # analisis dampak
        print("[+] menganalisis dampak serangan...")
        skor_dampak = analisis_dampak(pohon_minimum, status_ddos)
        
        # tampilkan node dengan dampak tertinggi
        print("\n[*] node dengan dampak tertinggi:")
        for node, skor in sorted(skor_dampak.items(), 
                               key=lambda x: x[1], reverse=True)[:3]:
            print(f"node {node}: skor dampak = {skor:.3f}")
        
        # tampilkan animasi
        print("\n[+] menampilkan animasi serangan...")
        print("\ntips: animasi akan disimpan sebagai gif")
        # jalanin animasi dan simpan sebagai gif
        anim = animasi_serangan(pohon_minimum, status_ddos)
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        output_path = os.path.join(assets_dir, 'simulasi_ddos.gif')

        print(f"\n[+] menyimpan animasi ke file '{output_path}'...")
        anim.save(output_path, writer='pillow')
        print(f"\n[+] selesai! coba buka file '{output_path}' di browser")
        
    except Exception as e:
        print("\n[!] waduh, ada error nih:")
        print(f"    {str(e)}")
        print("\n[!] coba cek apakah semua library sudah terinstall:")
        print("    pip install networkx numpy matplotlib")

if __name__ == "__main__":
    utama()
