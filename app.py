#!/usr/bin/env python3
"""
CD Vault - PocketBase Python Sync Web Application
Author: AI Studio Assistant

Dependencies:
    pip install Flask requests

Usage:
    python app.py
"""

import os
import secrets
import sys
import uuid
import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash

try:
    import requests
except ImportError:
    print("Error: 'requests' package not installed.", file=sys.stderr)
    print("Please run: pip install requests", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__)
# Signs the session cookie carrying flash messages. A per-process random key is the safe
# default; set FLASK_SECRET_KEY to keep flashes alive across a restart.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_urlsafe(32)

# Local PocketBase configurations matched to your local device server
POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://127.0.0.1:8090")
COLLECTION_NAME = "audiocd"

# Smart caching and dynamic resolution of internal PocketBase container networking
_cached_internal_url = None

def clear_pocketbase_cache():
    global _cached_internal_url
    _cached_internal_url = None

def get_pocketbase_internal_url():
    global _cached_internal_url
    if _cached_internal_url is not None:
        return _cached_internal_url
    
    # Check explicit internal URL environment variable override first
    env_internal = os.environ.get("POCKETBASE_INTERNAL_URL")
    if env_internal:
        print(f"[PocketBase Network] Using explicit POCKETBASE_INTERNAL_URL: {env_internal}")
        _cached_internal_url = env_internal
        return env_internal

    from urllib.parse import urlparse
    try:
        parsed = urlparse(POCKETBASE_URL)
        port = parsed.port or 8090
    except Exception:
        port = 8090
    
    # Candidate internal connection URLs for Docker/Podman same-network container resolution
    candidates = [
        POCKETBASE_URL,
        f"http://pocketbase:{port}",
        f"http://pocketbase-server:{port}",
        f"http://host.docker.internal:{port}",
        f"http://172.17.0.1:{port}",
        f"http://127.0.0.1:{port}"
    ]
    
    # Deduplicate candidates while preserving order
    seen = set()
    dedup_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            dedup_candidates.append(c)
            
    print(f"[PocketBase Network] Probing candidates for internal resolution: {dedup_candidates}")
    for url in dedup_candidates:
        probe_urls = [
            f"{url}/api/collections/{COLLECTION_NAME}/records?perPage=1",
            f"{url}/api/health"
        ]
        for probe_url in probe_urls:
            try:
                # Use a larger 1.5s timeout for network & DNS resolution in container environments
                print(f"[PocketBase Network] Probing {probe_url} ...")
                response = requests.get(probe_url, timeout=1.5)
                # Any response status of 200, 400, 403, or 404 indicates a running server responded
                if response.status_code in [200, 204, 400, 403, 404]:
                    print(f"[PocketBase Network] Success! Connected internally to: {url} (status: {response.status_code})")
                    _cached_internal_url = url
                    return url
                else:
                    print(f"[PocketBase Network] Connected to {url} but got unexpected status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"[PocketBase Network] Probe to {probe_url} failed: {e}")
            
    # Fallback to standard POCKETBASE_URL if no connection probe is successful
    print(f"[PocketBase Network] No probes succeeded. Falling back to POCKETBASE_URL: {POCKETBASE_URL}")
    _cached_internal_url = POCKETBASE_URL
    return POCKETBASE_URL

@app.route("/api/files/<collection_id>/<record_id>/<filename>", methods=["GET"])
def proxy_pb_file(collection_id, record_id, filename):
    internal_url = get_pocketbase_internal_url()
    pb_file_url = f"{internal_url}/api/files/{collection_id}/{record_id}/{filename}"
    try:
        response = requests.get(pb_file_url, stream=True, timeout=5.0)
        from flask import Response
        headers = {}
        if "Content-Type" in response.headers:
            headers["Content-Type"] = response.headers["Content-Type"]
        if "Content-Length" in response.headers:
            headers["Content-Length"] = response.headers["Content-Length"]
            
        def generate():
            for chunk in response.iter_content(chunk_size=4096):
                yield chunk
                
        return Response(generate(), status=response.status_code, headers=headers)
    except Exception as e:
        print(f"[PocketBase File Proxy Error] Failed to proxy file {filename}: {e}")
        return "File not found or pocketbase offline", 404

# High-fidelity offline demo items in case PocketBase is offline or empty initially
FALLBACK_ITEMS = [
    {
        "id": "rogalddldziwki1",
        "collectionId": "pbc_386466699",
        "collectionName": "audiocd",
        "album": "dziwki dragi",
        "author": "rogal ddl",
        "cdcondition": 7,
        "covercondition": 6,
        "price": "120",
        "file": ["4893993211067_wbo037jmba.jpg"],
        "created": "2026-07-11 21:53:30.554Z",
        "updated": "2026-07-11 21:53:30.554Z"
    },
    {
        "id": "pezetnoonmuzyka",
        "collectionId": "pbc_386466699",
        "collectionName": "audiocd",
        "album": "Muzyka Klasyczna",
        "author": "Pezet-Noon",
        "cdcondition": 9,
        "covercondition": 8,
        "price": "320",
        "file": [],
        "created": "2026-07-11 20:10:15.000Z",
        "updated": "2026-07-11 20:10:15.000Z"
    },
    {
        "id": "nirvananevermind",
        "collectionId": "pbc_386466699",
        "collectionName": "audiocd",
        "album": "Nevermind",
        "author": "Nirvana",
        "cdcondition": 8,
        "covercondition": 7,
        "price": "95",
        "file": [],
        "created": "2026-07-11 18:42:00.000Z",
        "updated": "2026-07-11 18:42:00.000Z"
    },
    {
        "id": "pinkfloyddark",
        "collectionId": "pbc_386466699",
        "collectionName": "audiocd",
        "album": "The Dark Side of the Moon",
        "author": "Pink Floyd",
        "cdcondition": 10,
        "covercondition": 9,
        "price": "150",
        "file": [],
        "created": "2026-07-11 15:30:22.000Z",
        "updated": "2026-07-11 15:30:22.000Z"
    }
]

def get_gradient_style(title, author_name):
    """Generates a unique, stable visual gradient background based on album title hash"""
    combined = f"{title} {author_name}"
    hash_val = sum(ord(c) for c in combined)
    h1 = abs(hash_val) % 360
    h2 = (h1 + 130) % 360
    return f"background: linear-gradient(135deg, hsl({h1}, 75%, 35%) 0%, hsl({h2}, 85%, 15%) 100%)"

def get_condition_label(rating):
    """Translates numerical condition ratings to standard Goldmine grading scale"""
    if rating == 10: return "Mint (M)"
    if rating == 9: return "Near Mint (NM)"
    if rating >= 7: return "Very Good (VG)"
    if rating >= 5: return "Good (G)"
    if rating >= 3: return "Fair (F)"
    return "Poor (P)"

def get_condition_color(rating):
    """Provides Tailwind CSS class pairs matching quality levels"""
    if rating >= 9: return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
    if rating >= 7: return "text-teal-400 bg-teal-500/10 border-teal-500/20"
    if rating >= 5: return "text-amber-400 bg-amber-500/10 border-amber-500/20"
    return "text-rose-400 bg-rose-500/10 border-rose-500/20"

def get_auth_user():
    """Resolves authenticated user from standard single sign-on / proxy headers"""
    env_override = os.environ.get("MOCK_AUTH_USER")
    if env_override:
        return env_override.strip()
    
    user = request.headers.get("Remote-User")
    if not user:
        user = request.headers.get("X-Webauth-User")
    if not user:
        user = request.headers.get("X-Forwarded-User")
    return user.strip() if user else None

# Inject helper functions directly into the Jinja template rendering environment
app.jinja_env.globals.update(
    get_gradient_style=get_gradient_style,
    get_condition_label=get_condition_label,
    get_condition_color=get_condition_color
)

# Responsive, high-fidelity HTML and Tailwind dashboard matching our React frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The CD Journal</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
                        serif: ['Lora', 'ui-serif', 'Georgia', 'serif'],
                        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
                    },
                    colors: {
                        stone: {
                            850: '#22201e',
                            950: '#121110',
                        }
                    }
                }
            }
        }
    </script>
    <script>
        // Check theme initially before body loads to prevent flash of light theme
        if (localStorage.getItem('theme') === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    </script>
</head>
<body class="min-h-screen bg-[#FBF9F6] dark:bg-[#121110] text-stone-900 dark:text-[#FAF8F5] flex flex-col font-sans selection:bg-stone-200 dark:selection:bg-stone-850 selection:text-stone-850 dark:selection:text-stone-100 transition-colors duration-300">
    
    <!-- Top utility bar -->
    <div class="max-w-7xl w-full mx-auto px-4 pt-4 md:px-8 flex justify-between items-center">
        <div>
            {% if connected %}
                <span class="text-[10px] font-mono font-bold text-emerald-800 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/40 px-2 py-1 uppercase tracking-wider">LIVE PARITY SYNCED</span>
            {% else %}
                <span class="text-[10px] font-mono font-bold text-amber-850 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2 py-1 uppercase tracking-wider">SANDBOX BACKUP</span>
            {% endif %}
        </div>
        <div class="flex items-center gap-3">
            {% if user %}
                <span class="text-[10px] font-mono font-bold text-emerald-800 dark:text-emerald-400 bg-emerald-105 dark:bg-emerald-950/40 px-2.5 py-1.5 border border-emerald-300 dark:border-emerald-800/80 uppercase tracking-wider">
                    USER: {{ user }}
                </span>
            {% else %}
                <span class="text-[10px] font-mono font-bold text-stone-500 bg-stone-100 dark:bg-stone-900 dark:text-stone-400 px-2.5 py-1.5 border border-stone-300 dark:border-stone-800/80 uppercase tracking-wider italic">
                    GUEST VIEW (READ-ONLY)
                </span>
            {% endif %}
            <button
                onclick="toggleTheme()"
                class="flex items-center gap-2 px-3 py-1.5 text-xs font-mono font-bold tracking-wider border border-stone-300 dark:border-stone-800 hover:border-stone-900 dark:hover:border-stone-100 transition-all cursor-pointer text-stone-700 dark:text-stone-300 bg-white dark:bg-[#1C1A17] shadow-sm"
                id="theme-btn"
            >
                <span id="theme-btn-text">DARK THEME</span>
            </button>
        </div>
    </div>

    <!-- Main App Layout -->
    <div class="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8 flex flex-col gap-6 md:gap-8">
        
        <!-- Navigation & Header -->
        <header class="flex flex-col justify-center items-center text-center gap-4 border-b-4 border-double border-stone-900 dark:border-stone-100 pb-6 pt-2">
            <div class="text-[10px] md:text-xs font-mono uppercase tracking-[0.2em] text-stone-500 dark:text-stone-400 flex items-center gap-2">
                <span>COLLECTOR'S EDITION ARCHIVE</span>
                <span>•</span>
                <span>EST. 2026</span>
                <span>•</span>
                <span class="text-stone-800 dark:text-stone-200 font-bold bg-stone-200 dark:bg-stone-800 px-1.5 py-0.5">V0.2</span>
                <span>•</span>
                <span class="text-emerald-800 dark:text-emerald-400 font-bold bg-emerald-100 dark:bg-emerald-950/40 px-1.5 py-0.5">{{ stats.count }} ITEMS</span>
            </div>
            <div class="flex flex-col items-center gap-1">
                <h1 class="text-4xl md:text-6xl font-serif font-black tracking-tight text-stone-900 dark:text-white uppercase">
                    The CD Journal
                </h1>
                <p class="text-stone-600 dark:text-stone-400 font-serif italic text-xs md:text-sm max-w-lg mt-1">
                    A high-fidelity printed index and diagnostic dashboard for your physical compact disc library.
                </p>
            </div>
            
            <!-- Thin divider line / information box -->
            <div class="w-full flex flex-col sm:flex-row justify-between items-center border-t border-b border-stone-300 dark:border-stone-800 py-2.5 mt-2 text-xs text-stone-500 dark:text-stone-400 font-mono tracking-wider gap-3">
                <div class="flex items-center gap-2">
                    <svg class="h-4 w-4 text-stone-800 dark:text-stone-200 animate-[spin_6s_linear_infinite]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="12" cy="12" r="10" stroke-width="2" />
                        <circle cx="12" cy="12" r="3" stroke-width="2" />
                        <path d="M12 2a10 10 0 0110 10" stroke-width="2" />
                    </svg>
                    <span>FORMAT: COMPACT DISC (12CM)</span>
                </div>
                <div class="flex items-center gap-4">
                    <span>COLLECTION ID: PBC_386466699</span>
                    <span class="hidden sm:inline">•</span>
                    <span class="text-stone-900 dark:text-stone-100 font-semibold uppercase">{% if connected %}LIVE SYNCED{% else %}SANDBOX FALLBACK{% endif %}</span>
                </div>
            </div>

            <!-- Add CD Quick Trigger Button -->
            {% if user %}
            <button
                onclick="openModal()"
                class="mt-2 bg-[#1C1A17] dark:bg-[#FAF8F5] text-white dark:text-stone-900 px-6 py-2.5 text-xs font-bold tracking-wider uppercase hover:opacity-90 transition-all cursor-pointer flex items-center gap-2"
            >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                <span>Add CD to Journal</span>
            </button>
            {% endif %}
        </header>

        <!-- Session Message Flashers -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="p-4 border text-xs font-bold uppercase tracking-wider {% if category == 'success' %}bg-[#EFECE6] border-stone-400 text-stone-900 dark:text-stone-100 dark:bg-stone-900 dark:border-stone-800{% else %}bg-rose-50 border-rose-300 text-rose-800 dark:bg-rose-950/30 dark:border-rose-900 dark:text-rose-400{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Utility Bar: Search & Filtering -->
        <div class="border border-stone-300 dark:border-stone-800 bg-white dark:bg-[#1C1A17] p-4 flex flex-col md:flex-row md:items-center gap-4 justify-between">
            <form action="/" method="GET" class="relative flex-1 max-w-md w-full flex gap-2">
                <div class="relative flex-1">
                    <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400 dark:text-stone-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <input
                        type="text"
                        name="q"
                        value="{{ search_query }}"
                        placeholder="Search album name or artist..."
                        class="w-full bg-[#FAF8F5] dark:bg-[#121110] border border-stone-300 dark:border-stone-800 rounded-none py-2 pl-10 pr-4 text-xs md:text-sm text-stone-900 dark:text-[#FAF8F5] placeholder-stone-400 dark:placeholder-stone-500 focus:outline-none focus:border-stone-900 dark:focus:border-stone-100 transition-colors font-sans"
                    />
                </div>
                <button type="submit" class="bg-[#1C1A17] dark:bg-[#FAF8F5] text-white dark:text-stone-900 text-xs font-bold uppercase tracking-wider px-5 py-2 hover:opacity-90 transition-colors">
                    Search
                </button>
            </form>
            
            {% if search_query %}
            <div>
                <a href="/" class="text-xs text-stone-800 dark:text-stone-200 hover:text-stone-950 dark:hover:text-white font-semibold underline underline-offset-4">
                    Clear Search Filters
                </a>
            </div>
            {% endif %}
        </div>

        <!-- CD Jewel Cards List -->
        {% if items|length == 0 %}
            <div class="bg-white dark:bg-[#1C1A17] border border-stone-300 dark:border-stone-800 rounded-none p-12 text-center flex flex-col items-center justify-center gap-3">
                <svg class="h-10 w-10 text-stone-400 dark:text-stone-500 animate-spin" style="animation-duration: 20s" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="10" stroke-width="2" />
                    <circle cx="12" cy="12" r="3" stroke-width="2" />
                    <path d="M12 2a10 10 0 0110 10" stroke-width="2" />
                </svg>
                <h3 class="text-lg font-serif font-bold text-stone-950 dark:text-white mt-2">No audio CDs found</h3>
                <p class="text-stone-600 dark:text-stone-400 text-xs md:text-sm max-sm font-sans">
                    {% if search_query %}No records match your search query.{% else %}Your collection is currently empty.{% endif %}
                </p>
            </div>
        {% else %}
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
                {% for item in items %}
                    {% set has_cover = item.file and item.file|length > 0 %}
                    <div class="group relative bg-white dark:bg-[#1C1A17] border border-stone-300 dark:border-stone-800 rounded-none p-5 flex flex-col justify-between hover:border-stone-950 dark:hover:border-stone-300 hover:shadow-lg dark:hover:shadow-black/40 transition-all duration-300">
                        
                        <!-- Floating Price Badge -->
                        <div class="absolute top-4 right-4 z-20 bg-stone-100 dark:bg-stone-900 border border-stone-300 dark:border-stone-800 text-stone-900 dark:text-stone-100 font-mono font-bold text-xs px-2.5 py-1 rounded-none">
                            {{ item.price }} PLN
                        </div>

                        <!-- Sliding Disc Jewel Case Cover -->
                        <div class="relative aspect-[4/3] w-full bg-[#FAF8F5] dark:bg-stone-900/40 rounded-none overflow-hidden mb-4 border border-stone-200 dark:border-stone-800 shadow-inner flex items-center justify-center">
                            
                            <!-- CD Tray/Holder (behind sleeve) -->
                            <div class="absolute right-3 top-1/2 -translate-y-1/2 w-40 h-40 rounded-full border border-stone-300 dark:border-stone-800 bg-stone-100 dark:bg-stone-900 flex items-center justify-center shadow-md transform translate-x-2 opacity-50 group-hover:translate-x-6 group-hover:opacity-100 transition-all duration-700">
                                <!-- Inner Vinyl Groove -->
                                <div class="w-36 h-36 rounded-full border border-stone-300 dark:border-stone-800 bg-stone-200 dark:bg-stone-950 flex items-center justify-center relative shadow-inner animate-[spin_12s_linear_infinite]">
                                    <div class="absolute inset-2 rounded-full border border-stone-300 dark:border-stone-800"></div>
                                    <div class="absolute inset-5 rounded-full border border-stone-300 dark:border-stone-800"></div>
                                    <div class="absolute inset-8 rounded-full border border-stone-300 dark:border-stone-800"></div>
                                    <div class="w-10 h-10 rounded-full bg-stone-100 dark:bg-stone-900 border border-stone-300 dark:border-stone-800 flex items-center justify-center">
                                        <div class="w-4 h-4 rounded-full bg-stone-300 dark:bg-stone-700 border border-stone-400 dark:border-stone-800"></div>
                                    </div>
                                </div>
                            </div>

                            <!-- Front Sleeve Album Cover (slides out slightly or shrinks back) -->
                            {% if has_cover and connected %}
                                <div class="absolute left-0 top-0 bottom-0 w-3/4 z-10 shadow-2xl transition-transform duration-500 ease-out group-hover:scale-[0.98] group-hover:translate-x-1" 
                                     style="background: url('/api/files/{{ item.collectionId }}/{{ item.id }}/{{ item.file[0] }}') center/cover no-repeat">
                                    <!-- Glossy overlay sheen -->
                                    <div class="absolute inset-0 bg-gradient-to-tr from-white/0 via-white/5 to-white/10 mix-blend-overlay"></div>
                                    <div class="absolute top-0 bottom-0 left-0 w-1.5 bg-gradient-to-r from-black/40 to-transparent"></div>
                                </div>
                            {% else %}
                                <div class="absolute left-0 top-0 bottom-0 w-3/4 z-10 shadow-2xl transition-transform duration-500 ease-out group-hover:scale-[0.98] group-hover:translate-x-1 flex flex-col justify-between p-4 border-r border-stone-300 dark:border-stone-800 text-stone-900 dark:text-[#FAF8F5] bg-[#EFECE6]" 
                                     style="{{ get_gradient_style(item.album, item.author) }}">
                                    <!-- Glossy overlay sheen -->
                                    <div class="absolute inset-0 bg-gradient-to-tr from-white/0 via-white/5 to-white/10 mix-blend-overlay"></div>
                                    <div class="absolute top-0 bottom-0 left-0 w-1.5 bg-gradient-to-r from-black/40 to-transparent"></div>
                                    <div class="flex items-start justify-between">
                                        <svg class="h-5 w-5 text-stone-700 dark:text-stone-300 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                            <circle cx="12" cy="12" r="10" stroke-width="2" />
                                            <circle cx="12" cy="12" r="3" stroke-width="2" />
                                            <path d="M12 2a10 10 0 0110 10" stroke-width="2" />
                                        </svg>
                                        <span class="text-[9px] font-mono tracking-widest text-stone-500 dark:text-stone-400 uppercase bg-stone-200/60 dark:bg-stone-800/60 px-1.5 py-0.5 rounded-none">CD FORMAT</span>
                                    </div>
                                    <div class="z-10 border-t border-stone-400 dark:border-stone-700 pt-3">
                                        <h4 class="font-serif font-black text-sm leading-tight tracking-tight text-stone-950 dark:text-white uppercase line-clamp-2">{{ item.album }}</h4>
                                        <p class="font-serif italic text-[11px] text-stone-700 dark:text-stone-300 mt-1 tracking-wide font-medium capitalize">{{ item.author }}</p>
                                    </div>
                                </div>
                            {% endif %}
                        </div>

                        <!-- Item details -->
                        <div class="flex flex-col gap-3">
                            <div>
                                <h3 class="font-serif font-black text-stone-900 dark:text-white group-hover:text-stone-950 dark:group-hover:text-amber-100 capitalize text-base tracking-tight truncate line-clamp-1">{{ item.album }}</h3>
                                <p class="text-stone-500 dark:text-stone-400 font-serif italic text-xs capitalize mt-0.5 tracking-wide truncate">{{ item.author }}</p>
                            </div>

                            <!-- Grading Condition Blocks -->
                            <div class="grid grid-cols-2 gap-2 pt-1 font-sans">
                                <div class="bg-[#FAF8F5] dark:bg-stone-900/50 border border-stone-200 dark:border-stone-800 rounded-none p-2 flex flex-col justify-between">
                                    <span class="text-[9px] font-mono text-stone-500 dark:text-stone-400 uppercase tracking-wider">CD Disc</span>
                                    <div class="flex items-baseline gap-1 mt-0.5">
                                        <span class="text-sm font-serif font-black text-stone-950 dark:text-white">{{ item.cdcondition }}</span>
                                        <span class="text-[10px] text-stone-400 dark:text-stone-500 font-mono">/10</span>
                                    </div>
                                    <span class="text-[9px] font-semibold mt-1 inline-block border px-1.5 py-0.5 rounded-none text-center text-stone-800 dark:text-stone-200 bg-stone-100 dark:bg-stone-800 border-stone-200/80 dark:border-stone-800">
                                        {{ get_condition_label(item.cdcondition|int) }}
                                    </span>
                                </div>

                                <div class="bg-[#FAF8F5] dark:bg-stone-900/50 border border-stone-200 dark:border-stone-800 rounded-none p-2 flex flex-col justify-between">
                                    <span class="text-[9px] font-mono text-stone-500 dark:text-stone-400 uppercase tracking-wider">Sleeve/Cover</span>
                                    <div class="flex items-baseline gap-1 mt-0.5">
                                        <span class="text-sm font-serif font-black text-stone-950 dark:text-white">{{ item.covercondition }}</span>
                                        <span class="text-[10px] text-stone-400 dark:text-stone-500 font-mono">/10</span>
                                    </div>
                                    <span class="text-[9px] font-semibold mt-1 inline-block border px-1.5 py-0.5 rounded-none text-center text-stone-800 dark:text-stone-200 bg-stone-100 dark:bg-stone-800 border-stone-200/80 dark:border-stone-800">
                                        {{ get_condition_label(item.covercondition|int) }}
                                    </span>
                                </div>
                            </div>

                            <!-- Date Added and Actions -->
                            <div class="flex items-center justify-between pt-3 border-t border-stone-200 dark:border-stone-800 text-[11px] text-stone-400 dark:text-stone-500 font-mono tracking-wider uppercase">
                                <span>ADDED {% if item.created %}{{ item.created[:10] }}{% else %}2026-07-11{% endif %}</span>
                                {% if user %}
                                <a href="/delete/{{ item.id }}" class="text-rose-600 hover:text-rose-500 font-bold hover:underline transition-colors flex items-center gap-1" onclick="return confirm('Are you sure you want to delete this CD?');">
                                    <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                    <span>DELETE</span>
                                </a>
                                {% endif %}
                            </div>
                        </div>

                    </div>
                {% endfor %}
            </div>
        {% endif %}

    </div>

    <!-- Add CD Modal -->
    {% if user %}
    <div id="add-modal" class="fixed inset-0 bg-stone-900/40 backdrop-blur-sm hidden items-center justify-center p-4 z-50">
        <div class="bg-white dark:bg-[#1C1A17] border-4 border-double border-stone-900 dark:border-stone-100 max-w-lg w-full overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div class="bg-[#FAF8F5] dark:bg-stone-900 border-b border-stone-300 dark:border-stone-800 px-6 py-4 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <svg class="h-5 w-5 text-stone-900 dark:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="12" cy="12" r="10" stroke-width="2" />
                        <circle cx="12" cy="12" r="3" stroke-width="2" />
                        <path d="M12 2a10 10 0 0110 10" stroke-width="2" />
                    </svg>
                    <h2 class="text-lg font-serif font-black text-stone-900 dark:text-white uppercase tracking-tight">Add CD to Journal</h2>
                </div>
                <button 
                    onclick="closeModal()"
                    class="text-stone-400 hover:text-stone-900 dark:hover:text-white font-bold hover:bg-stone-100 dark:hover:bg-stone-800 px-2.5 py-1.5 rounded-none text-sm transition-colors cursor-pointer"
                >
                    ✕
                </button>
            </div>

            <form action="/add" method="POST" enctype="multipart/form-data" class="p-6 flex flex-col gap-4 font-sans">
                <!-- Form Input fields -->
                <div class="grid grid-cols-2 gap-4">
                    <div class="col-span-2">
                        <label class="block text-stone-700 dark:text-stone-300 text-xs font-mono uppercase tracking-wider mb-1.5">Album Title *</label>
                        <input
                            type="text"
                            name="album"
                            placeholder="e.g. dziwki dragi"
                            required
                            class="w-full bg-[#FAF8F5] dark:bg-[#121110] border border-stone-300 dark:border-stone-800 rounded-none px-3.5 py-2 text-xs md:text-sm text-stone-900 dark:text-stone-100 focus:outline-none focus:border-stone-900 dark:focus:border-stone-100 transition-colors"
                        />
                    </div>

                    <div class="col-span-2">
                        <label class="block text-stone-700 dark:text-stone-300 text-xs font-mono uppercase tracking-wider mb-1.5">Artist / Author *</label>
                        <input
                            type="text"
                            name="author"
                            placeholder="e.g. rogal ddl"
                            required
                            class="w-full bg-[#FAF8F5] dark:bg-[#121110] border border-stone-300 dark:border-stone-800 rounded-none px-3.5 py-2 text-xs md:text-sm text-stone-900 dark:text-stone-100 focus:outline-none focus:border-stone-900 dark:focus:border-stone-100 transition-colors"
                        />
                    </div>

                    <div>
                        <label class="block text-stone-700 dark:text-stone-300 text-xs font-mono uppercase tracking-wider mb-1.5 font-bold">CD Condition (1-10)</label>
                        <div class="flex items-center gap-2">
                            <input
                                type="range"
                                min="1"
                                max="10"
                                name="cdcondition"
                                value="8"
                                oninput="document.getElementById('cd-val').innerText = this.value"
                                class="w-full h-1 bg-stone-300 dark:bg-stone-800 rounded-none appearance-none cursor-pointer accent-stone-900 dark:accent-stone-100"
                            />
                            <span id="cd-val" class="text-sm font-bold font-serif text-stone-950 dark:text-white min-w-[20px]">8</span>
                        </div>
                    </div>

                    <div>
                        <label class="block text-stone-700 dark:text-stone-300 text-xs font-mono uppercase tracking-wider mb-1.5 font-bold">Cover Condition (1-10)</label>
                        <div class="flex items-center gap-2">
                            <input
                                type="range"
                                min="1"
                                max="10"
                                name="covercondition"
                                value="8"
                                oninput="document.getElementById('cover-val').innerText = this.value"
                                class="w-full h-1 bg-stone-300 dark:bg-stone-800 rounded-none appearance-none cursor-pointer accent-stone-900 dark:accent-stone-100"
                            />
                            <span id="cover-val" class="text-sm font-bold font-serif text-stone-950 dark:text-white min-w-[20px]">8</span>
                        </div>
                    </div>

                    <div class="col-span-2">
                        <label class="block text-stone-700 dark:text-stone-300 text-xs font-mono uppercase tracking-wider mb-1.5">Price (PLN)</label>
                        <input
                            type="number"
                            name="price"
                            placeholder="e.g. 120"
                            class="w-full bg-[#FAF8F5] dark:bg-[#121110] border border-stone-300 dark:border-stone-800 rounded-none px-3.5 py-2 text-xs md:text-sm text-stone-950 dark:text-stone-100 focus:outline-none focus:border-stone-900 dark:focus:border-stone-100 transition-colors font-mono"
                        />
                    </div>

                    <div class="col-span-2">
                        <label class="block text-stone-700 dark:text-stone-300 text-xs font-mono uppercase tracking-wider mb-1.5">Cover File</label>
                        <input
                            type="file"
                            name="file"
                            accept="image/*"
                            class="w-full bg-[#FAF8F5] dark:bg-[#121110] border border-stone-300 dark:border-stone-800 rounded-none px-3.5 py-2 text-xs text-stone-600 dark:text-stone-400 focus:outline-none focus:border-stone-900 dark:focus:border-stone-100 transition-colors file:mr-4 file:py-1 file:px-3 file:rounded-none file:border file:border-stone-400 file:text-xs file:font-mono file:bg-white dark:file:bg-stone-900 file:text-stone-800 dark:file:text-stone-200 hover:file:bg-stone-50"
                        />
                    </div>
                </div>

                <!-- Form Actions -->
                <div class="flex items-center justify-end gap-3 mt-4 border-t border-stone-300 dark:border-stone-800 pt-4">
                    <button
                        type="button"
                        onclick="closeModal()"
                        class="bg-white dark:bg-stone-900 border border-stone-300 dark:border-stone-800 text-stone-700 dark:text-stone-300 font-semibold text-xs md:text-sm px-4 py-2.5 rounded-none hover:bg-stone-50 dark:hover:bg-stone-800 transition-colors cursor-pointer"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        class="bg-[#1C1A17] dark:bg-[#FAF8F5] text-white dark:text-stone-900 font-bold text-xs md:text-sm px-6 py-2.5 rounded-none transition-all flex items-center gap-2 uppercase tracking-wider border border-stone-900 cursor-pointer"
                    >
                        <span>Add to Collection</span>
                    </button>
                </div>
            </form>
        </div>
    </div>
    {% endif %}

    <!-- Footer -->
    <footer class="bg-stone-900 text-stone-400 border-t border-stone-850 py-6 px-4 text-center text-xs font-mono mt-12">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-2">
            <span>CD JOURNAL COLLECTION MANAGEMENT SYSTEM • EST. 2026</span>
            <span class="text-stone-500">Configured to poll local dev-server at {{ pb_url }}</span>
        </div>
    </footer>

    <!-- Theme and Modal Logic Scripts -->
    <script>
        function toggleTheme() {
            const htmlClass = document.documentElement.classList;
            if (htmlClass.contains('dark')) {
                htmlClass.remove('dark');
                localStorage.setItem('theme', 'light');
                updateThemeButtonText(false);
            } else {
                htmlClass.add('dark');
                localStorage.setItem('theme', 'dark');
                updateThemeButtonText(true);
            }
        }

        function updateThemeButtonText(isDark) {
            const btnText = document.getElementById('theme-btn-text');
            if (btnText) {
                btnText.innerText = isDark ? 'LIGHT THEME' : 'DARK THEME';
            }
        }

        // Sync button text on load
        document.addEventListener('DOMContentLoaded', () => {
            const isDark = document.documentElement.classList.contains('dark');
            updateThemeButtonText(isDark);
        });

        // Modal triggers
        function openModal() {
            const modal = document.getElementById('add-modal');
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }

        function closeModal() {
            const modal = document.getElementById('add-modal');
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    search_query = request.args.get("q", "").strip()
    connected = False
    items = []

    internal_url = get_pocketbase_internal_url()
    try:
        # Fetch actual live data from local PocketBase
        url = f"{internal_url}/api/collections/{COLLECTION_NAME}/records?sort=-created"
        response = requests.get(url, timeout=1.0)
        if response.status_code == 200:
            connected = True
            items = response.json().get("items", [])
        else:
            print(f"[PocketBase Index Error] Fetch from {url} returned status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[PocketBase Index Error] Failed to fetch items from {internal_url}: {e}")
        connected = False
        clear_pocketbase_cache()

    # Gracefully fall back to local offline items if disconnected
    if not connected:
        items = FALLBACK_ITEMS

    # Handle searching query parameters
    if search_query:
        q_lower = search_query.lower()
        items = [
            item for item in items 
            if q_lower in item.get("album", "").lower() or q_lower in item.get("author", "").lower()
        ]

    # Calculate collection metrics
    stats = {
        "count": len(items),
        "avg_cd": 0.0,
        "avg_cover": 0.0,
        "total_value": 0
    }
    
    if items:
        total_cd = sum(int(item.get("cdcondition", 0)) for item in items)
        total_cover = sum(int(item.get("covercondition", 0)) for item in items)
        total_value = sum(int(float(item.get("price", "0") or "0")) for item in items)
        stats["avg_cd"] = round(total_cd / len(items), 1)
        stats["avg_cover"] = round(total_cover / len(items), 1)
        stats["total_value"] = total_value

    return render_template_string(
        HTML_TEMPLATE, 
        items=items, 
        search_query=search_query, 
        connected=connected, 
        pb_url=POCKETBASE_URL, 
        stats=stats,
        user=get_auth_user()
    )


@app.route("/add", methods=["POST"])
def add_cd():
    if not get_auth_user():
        flash("Authorization failed. You must be logged in to add items to the collection.", "error")
        return redirect(url_for("index"))

    album = request.form.get("album", "").strip()
    author = request.form.get("author", "").strip()
    cd_cond = request.form.get("cdcondition", "8").strip()
    cover_cond = request.form.get("covercondition", "8").strip()
    price = request.form.get("price", "0").strip()
    
    file_upload = request.files.get("file")

    internal_url = get_pocketbase_internal_url()
    try:
        # Forward the multipart payload straight into your local PocketBase instance
        payload = {
            "album": album,
            "author": author,
            "cdcondition": cd_cond,
            "covercondition": cover_cond,
            "price": price
        }
        
        files = None
        if file_upload and file_upload.filename:
            files = {"file": (file_upload.filename, file_upload.read(), file_upload.content_type)}

        response = requests.post(
            f"{internal_url}/api/collections/{COLLECTION_NAME}/records",
            data=payload,
            files=files,
            timeout=1.5
        )

        if response.status_code in [200, 201]:
            flash("CD successfully saved directly to your local PocketBase!", "success")
        else:
            print(f"[PocketBase Add Error] Server returned {response.status_code}: {response.text}")
            flash(f"PocketBase returned an API error: {response.text}", "error")
    except requests.exceptions.RequestException as e:
        print(f"[PocketBase Add Error] Failed to connect: {e}")
        # Seamless offline backup creation
        mock_id = f"mock_{uuid.uuid4().hex[:8]}"
        mock_item = {
            "id": mock_id,
            "collectionId": "pbc_386466699",
            "collectionName": "audiocd",
            "album": album,
            "author": author,
            "cdcondition": int(cd_cond),
            "covercondition": int(cover_cond),
            "price": price,
            "file": [],
            "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%SZ"),
            "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%SZ")
        }
        FALLBACK_ITEMS.insert(0, mock_item)
        flash("PocketBase offline. Added CD to local memory backup!", "success")

    return redirect(url_for("index"))


@app.route("/delete/<record_id>")
def delete_cd(record_id):
    if not get_auth_user():
        flash("Authorization failed. You must be logged in to remove items from the collection.", "error")
        return redirect(url_for("index"))

    internal_url = get_pocketbase_internal_url()
    try:
        response = requests.delete(
            f"{internal_url}/api/collections/{COLLECTION_NAME}/records/{record_id}",
            timeout=1.0
        )
        if response.status_code == 204:
            flash("CD removed from collection!", "success")
        else:
            print(f"[PocketBase Delete Error] Server returned {response.status_code}: {response.text}")
            remove_from_fallback(record_id)
            flash("Removed item from local memory.", "success")
    except requests.exceptions.RequestException as e:
        print(f"[PocketBase Delete Error] Failed to connect: {e}")
        remove_from_fallback(record_id)
        flash("PocketBase offline. Removed item from local memory.", "success")

    return redirect(url_for("index"))

def remove_from_fallback(record_id):
    global FALLBACK_ITEMS
    FALLBACK_ITEMS = [item for item in FALLBACK_ITEMS if item.get("id") != record_id]


if __name__ == "__main__":
    # Runs on standard port 5000 by default (or environment-supplied port)
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting CD Vault Python server on port {port}...")
    app.run(host=host, port=port, debug=True)
