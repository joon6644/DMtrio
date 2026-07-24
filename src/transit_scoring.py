import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import folium

def gaussian_decay_weight(d, R):
    """
    Normalized Gaussian Decay Weight Function:
    W(d, R) = [exp(-0.5 * (d/R)^2) - exp(-0.5)] / [1 - exp(-0.5)]  for 0 <= d <= R
    W(d, R) = 0  for d > R
    """
    d = np.asarray(d, dtype=float)
    r_val = float(R)
    
    denom = 1.0 - np.exp(-0.5)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = d / r_val
        exponent = -0.5 * (ratio ** 2)
        weight = (np.exp(exponent) - np.exp(-0.5)) / denom
    
    weight = np.where((d >= 0) & (d <= r_val), weight, 0.0)
    return np.clip(weight, 0.0, 1.0)

def calculate_facility_score(
    base_score: float = 10.0,
    passengers: np.ndarray = None,
    scaling_mode: str = "log",  # 'log', 'sqrt', 'linear', 'minmax'
    passenger_weight: float = 1.0,
    max_additional_score: float = 50.0
) -> np.ndarray:
    """
    Calculates total facility score = Base Score + Additional Score (Passenger scaling).
    - base_score: 기본 점수 (기본 교통기능 보장)
    - passengers: 승하차 인원 배열
    - scaling_mode: 승하차인원 스케일링 방식 ('log', 'sqrt', 'linear', 'minmax')
    - passenger_weight: 추가 점수 가중치 곱선
    - max_additional_score: 추가 점수 상한선 (캡핑)
    """
    if passengers is None or len(passengers) == 0:
        return np.full_like(passengers, base_score, dtype=float)
    
    p = np.nan_to_num(passengers, nan=0.0)
    p = np.maximum(p, 0.0)
    
    if scaling_mode == "log":
        # log1p scaling
        add_score = np.log1p(p) * passenger_weight
    elif scaling_mode == "sqrt":
        add_score = np.sqrt(p) * passenger_weight
    elif scaling_mode == "linear":
        add_score = p * passenger_weight
    elif scaling_mode == "minmax":
        p_max = np.max(p) if np.max(p) > 0 else 1.0
        add_score = (p / p_max) * max_additional_score * passenger_weight
    else:
        add_score = np.zeros_like(p)
        
    if max_additional_score is not None and max_additional_score > 0:
        add_score = np.minimum(add_score, max_additional_score)
        
    return base_score + add_score

def plot_gaussian_decay_curve(save_path: str = None):
    """
    Plots the 1D Gaussian Decay curve for Bus (400m) and Subway (800m) with benchmark points.
    """
    d_bus = np.linspace(0, 500, 500)
    w_bus = gaussian_decay_weight(d_bus, R=400)
    
    d_sub = np.linspace(0, 1000, 500)
    w_sub = gaussian_decay_weight(d_sub, R=800)
    
    plt.figure(figsize=(10, 5), facecolor='#111827')
    ax = plt.gca()
    ax.set_facecolor('#111827')
    
    plt.plot(d_bus, w_bus, label='Bus (R=400m)', color='#3b82f6', linewidth=2.5)
    plt.plot(d_sub / 2, w_sub, label='Subway (R=800m, Normalized Distance)', color='#a855f7', linewidth=2.5, linestyle='--')
    
    ratios = [0.0, 0.25, 0.50, 0.75, 1.00]
    for r in ratios:
        w_val = gaussian_decay_weight(r * 400, 400)
        plt.scatter(r * 400, w_val, color='#f59e0b', s=50, zorder=5)
        plt.annotate(f"{r*100:.0f}% ({w_val:.2f})", (r * 400, w_val),
                     textcoords="offset points", xytext=(0,10), ha='center',
                     color='white', fontsize=9, fontweight='bold')
        
    plt.title("Normalized Gaussian Distance Decay Function W(d, R)", color='white', fontsize=14, pad=15)
    plt.xlabel("Distance d (m) [Bus]", color='#9ca3af', fontsize=11)
    plt.ylabel("Weight W(d, R)", color='#9ca3af', fontsize=11)
    plt.grid(True, linestyle=':', alpha=0.3, color='#4b5563')
    plt.legend(facecolor='#1f2937', labelcolor='white', edgecolor='none')
    plt.tick_params(colors='#9ca3af')
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == '__main__':
    print("Testing Gaussian Decay Weights...")
    ratios = [0.0, 0.25, 0.50, 0.75, 1.00]
    for r in ratios:
        w_b = gaussian_decay_weight(r * 400, 400)
        w_s = gaussian_decay_weight(r * 800, 800)
        print(f"Ratio {r*100:3.0f}% | Bus ({r*400:3.0f}m): {w_b:.4f} | Subway ({r*800:3.0f}m): {w_s:.4f}")
