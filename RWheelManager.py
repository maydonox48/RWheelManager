from phBot import *
import QtBind
import json
import os
import random
import re
import sqlite3
import struct
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from threading import Timer, RLock


pName = 'RWheelManager'
pVersion = '2.1.0.1'
pDeveloper = '_Apache_'
# Baska bir eklentiyi temel aldiysan buraya adini yaz (ornek: 'FascinaTe');
# baslik cubugunda "Temel: ..." olarak gorunur. Bos birakirsan gorunmez.
pBaseCredit = ''

OPCODE_REQUEST = 0x7151
OPCODE_RESPONSE = 0xB151

# --- Gorunum -----------------------------------------------------------
INK = '#14161f'          # koyu seritler (baslik, durum cubugu)
GOLD = '#f2c14e'         # vurgu
PAPER = '#f5f2ea'        # acik kartlar
PAPER_TEXT = '#2a2620'
PAPER_MUTED = '#7d7668'
DARK_MUTED = '#8d93a6'
CARD_DARK = '#1b1e2b'    # canli durum karti
BAR_EMPTY = '#34384a'
ACCENT = {'fate': '#8b6cf0', 'fortune': '#2fb383', 'pen': '#e08a2e'}
LEVEL_DARK = {'ok': '#5fe3a1', 'warn': '#ffc857', 'err': '#ff6b7a', 'muted': '#9aa0b4'}
LEVEL_LIGHT = {'ok': '#1f9d63', 'warn': '#c98a1a', 'err': '#d93a4d', 'muted': '#7d7668'}
OFFSCREEN_X = 3000
MAX_LINES = 32
MAX_TARGET_VALUE = 2147483647

MODES = ('fate', 'fortune', 'pen')
MODE_LABELS = {'fate': 'Fate', 'fortune': 'Fortune', 'pen': 'Pen'}
CONSUMABLE_NAMES = {
    'fate': ('Wheel of Fate',),
    'fortune': ('Wheel of Fortune',),
    'pen': ('Feather Pen of Fortune',)
}

# --- Ayarlar -----------------------------------------------------------
DEFAULT_SETTINGS = {
    'delay_fate': 550, 'delay_fortune': 450, 'delay_pen': 1550,
    'next_item': 850, 'timeout': 10,
    'jitter': True, 'confirm': True, 'precheck': True
}
MIN_DELAY_MS = {'fate': 300, 'fortune': 300, 'pen': 1500}
MAX_DELAY_MS = 10000
settings = dict(DEFAULT_SETTINGS)

WEAPON_STATS = ['STR', 'INT', 'Durability', 'Attack Rate', 'Evade Block', 'Critical']
SHIELD_STATS = ['STR', 'INT', 'Durability', 'Evade Critical', 'Block']
ARMOR_STATS = {
    1: ['STR', 'INT', 'Durability', 'Parry Ratio', 'HP', 'MP'],
    2: ['STR', 'INT', 'Durability', 'Parry Ratio'],
    3: ['STR', 'INT', 'Durability', 'Parry Ratio', 'HP', 'MP', 'HP/MP Recovery'],
    4: ['STR', 'INT', 'Durability', 'Parry Ratio', 'HP', 'MP'],
    5: ['STR', 'INT', 'Durability', 'Parry Ratio'],
    6: ['STR', 'INT', 'Durability', 'Parry Ratio']
}
ACCESSORY_BASE_STATS = [
    'STR', 'INT', 'Frostbite Resist', 'Fire Resist', 'Lightning Resist',
    'Poison Resist', 'Zombie Resist'
]
ACCESSORY_STATS = {
    1: ACCESSORY_BASE_STATS + ['CSMP Resist', 'Sleep Resist'],
    2: ACCESSORY_BASE_STATS + ['Stun Resist'],
    3: ACCESSORY_BASE_STATS + ['Disease Resist', 'Fear Resist']
}
WEAPON_NAMES = {
    2: 'Sword', 3: 'Blade', 4: 'Spear', 5: 'Glaive', 6: 'Bow',
    7: 'One-handed Sword', 8: 'Two-handed Sword', 9: 'Axe',
    10: 'Warlock Rod', 11: 'Staff', 12: 'Crossbow', 13: 'Dagger',
    14: 'Harp', 15: 'Cleric Rod'
}
ARMOR_NAMES = {1: 'Head', 2: 'Shoulder', 3: 'Chest', 4: 'Legs', 5: 'Hands', 6: 'Foot'}
ACCESSORY_NAMES = {1: 'Earring', 2: 'Necklace', 3: 'Ring'}

CLASSIC_CODES = {
    0x0A: 'STR', 0x0B: 'INT', 0x0C: 'Durability', 0x0F: 'Evade Critical',
    0x10: 'Parry Ratio', 0x11: 'HP', 0x12: 'MP', 0x13: 'Frostbite Resist',
    0x14: 'Lightning Resist', 0x15: 'Fire Resist', 0x16: 'Poison Resist',
    0x17: 'Zombie Resist', 0x19: 'Block', 0x1A: 'Stun Resist',
    0x1C: 'CSMP Resist', 0x1D: 'Disease Resist', 0x1E: 'Sleep Resist',
    0x1F: 'Fear Resist', 0x39: 'STR', 0x53: 'STR', 0x54: 'STR',
    0x55: 'STR', 0x3A: 'INT', 0x56: 'INT', 0x57: 'INT', 0x58: 'INT',
    0x3B: 'Durability', 0x59: 'Durability', 0x5A: 'Durability',
    0x47: 'Critical', 0x7D: 'Critical', 0x7E: 'Critical',
    0x3C: 'Attack Rate', 0x5C: 'Attack Rate', 0x3D: 'Block Rate',
    0x5F: 'Block Rate', 0x40: 'HP', 0x68: 'HP', 0x41: 'MP', 0x6B: 'MP',
    0x49: 'Stun', 0x4A: 'HP/MP Recovery', 0x4B: 'Combustion',
    0x4C: 'Disease', 0x4D: 'Sleep', 0x4E: 'Fear'
}
# High-degree weapon family verified from this server's Fortune responses.
# These codes overlap with classic meanings, so they must only be applied
# after the selected item has been classified as a weapon.
WEAPON_CONTEXT_CODES = {
    0x69: 'STR', 0x6A: 'INT', 0x6B: 'Durability',
    0x6C: 'Attack Rate', 0x6D: 'Evade Block', 0x77: 'Critical'
}
DG12_CODES = {
    0x0049: 'STR', 0x004F: 'INT', 0x0067: 'Attack Rate',
    0x0073: 'Evade Block', 0x008B: 'HP', 0x0097: 'MP', 0x010C: 'Critical'
}
IGNORED_RESPONSE_STATS = {'Athanasia', 'Solid', 'Luck', 'Repair'}
PEN_STAT_CODES = {
    0x39: 'STR', 0x53: 'STR', 0x54: 'STR', 0x55: 'STR',
    0x3A: 'INT', 0x56: 'INT', 0x57: 'INT', 0x58: 'INT',
    0x3B: 'Durability', 0x59: 'Durability', 0x5A: 'Durability',
    0x3C: 'Attack Rate', 0x5C: 'Attack Rate', 0x3D: 'Evade Block',
    0x5F: 'Evade Block', 0x3E: 'Evade Critical', 0x3F: 'Parry Ratio',
    0x65: 'Parry Ratio', 0x40: 'HP', 0x68: 'HP', 0x41: 'MP', 0x6B: 'MP',
    0x42: 'Frostbite Resist', 0x43: 'Lightning Resist', 0x44: 'Fire Resist',
    0x45: 'Poison Resist', 0x46: 'Zombie Resist', 0x47: 'Critical',
    0x7D: 'Critical', 0x7E: 'Critical', 0x48: 'Block', 0x49: 'Stun Resist',
    0x4A: 'HP/MP Recovery', 0x4B: 'Combustion Resist', 0x4C: 'Disease Resist',
    0x4D: 'Sleep Resist', 0x4E: 'Fear Resist'
}
PEN_STATS = []
for _name in PEN_STAT_CODES.values():
    if _name not in PEN_STATS:
        PEN_STATS.append(_name)

# phBot eşya verisinde mavi satırların hangi alanda durduğu belgelenmemiş;
# bilinen olası alan adlarını dene, bulunamazsa özellik pasif kalır.
BLUE_FIELD_NAMES = ('blues', 'blue', 'magic', 'magic_options', 'magicoptions',
                    'magic_option', 'options', 'attributes', 'stats')
STAT_ALIASES = [
    (re.compile(r'evade\s*block', re.I), 'Evade Block'),
    (re.compile(r'evade\s*crit', re.I), 'Evade Critical'),
    (re.compile(r'hp\s*/\s*mp|recover', re.I), 'HP/MP Recovery'),
    (re.compile(r'attack\s*rate|hit\s*rate|\bhr\b', re.I), 'Attack Rate'),
    (re.compile(r'parry|\ber\b', re.I), 'Parry Ratio'),
    (re.compile(r'frostbite', re.I), 'Frostbite Resist'),
    (re.compile(r'fire|burn', re.I), 'Fire Resist'),
    (re.compile(r'lightning|shock', re.I), 'Lightning Resist'),
    (re.compile(r'poison', re.I), 'Poison Resist'),
    (re.compile(r'zombie', re.I), 'Zombie Resist'),
    (re.compile(r'csmp', re.I), 'CSMP Resist'),
    (re.compile(r'sleep', re.I), 'Sleep Resist'),
    (re.compile(r'stun', re.I), 'Stun Resist'),
    (re.compile(r'disease', re.I), 'Disease Resist'),
    (re.compile(r'fear', re.I), 'Fear Resist'),
    (re.compile(r'durab', re.I), 'Durability'),
    (re.compile(r'crit', re.I), 'Critical'),
    (re.compile(r'block', re.I), 'Block'),
    (re.compile(r'\bstr\b|strength', re.I), 'STR'),
    (re.compile(r'\bint\b|intelligence', re.I), 'INT'),
    (re.compile(r'\bhp\b|health', re.I), 'HP'),
    (re.compile(r'\bmp\b|mana', re.I), 'MP'),
]

states = {}
for _mode in MODES:
    states[_mode] = {
        'inventory': [], 'queue': [], 'targets': [], 'available': [],
        'selected': None, 'index': 0, 'last_result': None
    }
test_items = {mode: None for mode in MODES}


def new_stats():
    return {'rolls': 0, 'started': None, 'ended': None, 'wheels_start': None,
            'best': None, 'best_text': '-'}


stats = {mode: new_stats() for mode in MODES}
history = deque(maxlen=200)
history_lock = RLock()
armed = {'mode': None, 'until': 0.0}

visible_mode = 'fate'
visible_page = 'setup'
active_mode = None
awaiting_response = False
single_roll = False
timer_token = 0
pending_timer = None
timeout_timer = None
request_id = 0
last_dash_refresh = 0.0
magic_option_codes = {}
magic_option_records = []
magic_database_path = None
magic_database_identity = None
debug_enabled = False
debug_path = None
debug_lock = RLock()
debug_last_request = None
DEBUG_MAX_BYTES = 10 * 1024 * 1024


# ======================================================================
# Debug
# ======================================================================
def debug_write(message):
    global debug_enabled
    with debug_lock:
        if not debug_enabled or not debug_path:
            return
        try:
            if os.path.getsize(debug_path) >= DEBUG_MAX_BYTES:
                raise ValueError('Debug file reached 10 MB; start a new capture')
            with open(debug_path, 'a', encoding='utf-8') as output:
                output.write('%s %s\n' % (datetime.now().isoformat(), message))
        except Exception:
            debug_enabled = False
            QtBind.setChecked(gui, chk_debug, False)
            set_status('Debug kaydı durdu: dosya yazılamadı veya 10 MB doldu', 'err')


def debug_changed(checked):
    global debug_enabled, debug_path, debug_last_request
    with debug_lock:
        if not checked:
            debug_write('CAPTURE STOPPED')
            debug_enabled = False
            set_status('Debug kaydı kapatıldı; dosya Log/RWheelManager içinde', 'muted')
            return
        try:
            folder = os.path.join(get_log_dir(), pName)
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, '%s_debug_%s_%d.txt' % (
                pName, datetime.now().strftime('%Y%m%d_%H%M%S_%f'), os.getpid()))
            with open(path, 'x', encoding='utf-8') as output:
                output.write('%s v%s diagnostic capture\n' % (pName, pVersion))
            debug_path = path
            debug_enabled = True
            debug_last_request = None
            character = get_character_data() or {}
            debug_write('SESSION ' + json.dumps({
                'server': character.get('server'), 'locale': get_locale(),
                'database': magic_database_path, 'database_codes': len(magic_option_codes),
                'settings': settings, 'active_mode': active_mode,
                'awaiting_response': awaiting_response}, ensure_ascii=True))
            set_status('Debug kaydı açık: Log/RWheelManager (Debug Klasörü ile aç)', 'ok')
        except Exception:
            debug_enabled = False
            QtBind.setChecked(gui, chk_debug, False)
            set_status('Debug dosyası phBot Log klasöründe oluşturulamadı', 'err')


def open_folder(folder):
    os.makedirs(folder, exist_ok=True)
    os.startfile(folder)


def debug_folder_clicked():
    try:
        folder = os.path.dirname(debug_path) if debug_path else os.path.join(get_log_dir(), pName)
        open_folder(folder)
        set_status('Debug klasörü açıldı; en son RWheelManager_debug_*.txt dosyasını gönder', 'ok')
    except Exception:
        set_status('Debug klasörü açılamadı: phBot Log/RWheelManager klasörüne bak', 'err')


def debug_packet(direction, opcode, data, source):
    global debug_last_request
    if not debug_enabled:
        return
    try:
        with debug_lock:
            now = time.monotonic()
            details = {'source': source, 'active_mode': active_mode,
                       'awaiting_response': awaiting_response, 'bytes': len(data),
                       'hex': ' '.join('%02X' % value for value in data[:4096]),
                       'truncated': len(data) > 4096}
            if direction == 'TX':
                debug_last_request = (now, source)
                if len(data) >= 5 and data[:3] == b'\x02\x19\x02':
                    for label, slot in (('item', data[3]), ('consumable', data[4])):
                        item = find_inventory_item(slot) or {}
                        details[label] = dict((key, item.get(key)) for key in
                                              ('model', 'name', 'servername', 'quantity', 'plus'))
                        details[label]['slot'] = slot
                if source == 'plugin' and active_mode:
                    details['target'] = active_item(active_mode)
            elif debug_last_request:
                details['ms_since_last_observed_request'] = round((now - debug_last_request[0]) * 1000, 1)
                details['last_request_source'] = debug_last_request[1]
                debug_last_request = None
            debug_write('%s 0x%04X %s' % (direction, opcode, json.dumps(details, ensure_ascii=True)))
    except Exception as error:
        debug_write('Capture metadata error: %s' % error)


def plugin_log(message):
    log('[%s] %s' % (pName, str(message)))


# ======================================================================
# Veritabani (magic option kimlikleri)
# ======================================================================
def readonly_database(path):
    if not os.path.isfile(path):
        # sqlite3.connect() would silently create an empty database file.
        raise IOError('Database file not found: %s' % path)
    try:
        # as_uri() percent-encodes spaces, '#', '%' and '?' in the path.
        uri = Path(os.path.abspath(path)).as_uri() + '?mode=ro'
        return sqlite3.connect(uri, uri=True)
    except Exception:
        # Some phBot embedded Python/SQLite builds do not expose URI mode.
        # query_only keeps the compatibility connection unable to mutate data.
        connection = sqlite3.connect(path)
        connection.execute('PRAGMA query_only = ON')
        return connection


def phbot_root_candidates():
    candidates = []
    raw_paths = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for getter in (get_config_dir, get_log_dir):
        try:
            folder = getter()
        except Exception:
            folder = None
        if folder:
            raw_paths.append(os.path.dirname(os.path.normpath(folder)))
    for path in raw_paths:
        current = os.path.abspath(path)
        for unused in range(3):
            if current not in candidates:
                candidates.append(current)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    return candidates


def normalized_identity(value):
    return ''.join(character.lower() for character in str(value or '') if character.isalnum())


def server_entry_matches(key, entry, active_server):
    active = normalized_identity(active_server)
    if not active:
        return False
    candidates = [key, entry.get('division')]
    candidates.extend(entry.get('servers', []))
    for candidate in candidates:
        value = normalized_identity(candidate)
        if value == active:
            return True
        if len(value) >= 4 and (value in active or active in value):
            return True
    return False


def normalized_path(value):
    return os.path.normcase(os.path.normpath(str(value or '').replace('/', os.sep)))


def active_database_path():
    locale = int(get_locale())
    character = get_character_data() or {}
    server = str(character.get('server') or '')
    if locale not in (18, 56) and not server:
        return None
    searched = []
    scan_errors = []
    for bot_path in phbot_root_candidates():
        data_path = os.path.join(bot_path, 'Data')
        if not os.path.isdir(data_path):
            continue
        searched.append(bot_path)
        if locale in (18, 56):
            filename = 'iSRO.db3' if locale == 18 else 'TRSRO.db3'
            path = os.path.join(data_path, filename)
            if os.path.isfile(path):
                return path
            continue
        try:
            with open(os.path.join(bot_path, 'vSRO.json'), 'r', encoding='utf-8') as source:
                servers = json.load(source)
        except Exception:
            continue
        media_path = None
        for key, entry in servers.items():
            if server_entry_matches(key, entry, server):
                media_path = entry.get('path')
                break
        if not media_path:
            continue
        try:
            names = sorted(name for name in os.listdir(data_path) if name.lower().endswith('.db3'))
        except Exception:
            continue
        for name in names:
            path = os.path.join(data_path, name)
            connection = None
            try:
                connection = readonly_database(path)
                database_paths = connection.execute(
                    'SELECT v FROM data WHERE k=?', ('path',)).fetchall()
                if any(normalized_path(row[0]) == normalized_path(media_path)
                       for row in database_paths):
                    return path
            except Exception as error:
                if len(scan_errors) < 3:
                    scan_errors.append('%s: %s' % (name, error))
            finally:
                if connection:
                    connection.close()
    if searched:
        plugin_log('No active database match for locale=%d server=%r under: %s' % (
            locale, server, ', '.join(searched)))
    if scan_errors:
        plugin_log('Database scan error(s): %s' % ' | '.join(scan_errors))
    return None


def canonical_magic_option(name, display):
    key = str(name or '').upper()
    exact = {
        'MATTR_STR': 'STR', 'MATTR_INT': 'INT', 'MATTR_DUR': 'Durability',
        'MATTR_HR': 'Attack Rate', 'MATTR_ER': 'Parry Ratio',
        'MATTR_EVADE_BLOCK': 'Evade Block', 'MATTR_EVADE_CRITICAL': 'Evade Critical',
        'MATTR_BLOCKRATE': 'Block', 'MATTR_CRITICAL': 'Critical',
        'MATTR_HP': 'HP', 'MATTR_MP': 'MP', 'MATTR_REGENHPMP': 'HP/MP Recovery',
        'MATTR_RESIST_FROSTBITE': 'Frostbite Resist',
        'MATTR_RESIST_BURN': 'Fire Resist', 'MATTR_RESIST_ESHOCK': 'Lightning Resist',
        'MATTR_RESIST_POISON': 'Poison Resist', 'MATTR_RESIST_ZOMBIE': 'Zombie Resist',
        'MATTR_RESIST_CSMP': 'CSMP Resist', 'MATTR_RESIST_SLEEP': 'Sleep Resist',
        'MATTR_RESIST_STUN': 'Stun Resist', 'MATTR_RESIST_DISEASE': 'Disease Resist',
        'MATTR_RESIST_FEAR': 'Fear Resist', 'MATTR_ATHANASIA': 'Athanasia',
        'MATTR_SOLID': 'Solid', 'MATTR_LUCK': 'Luck', 'MATTR_REPAIR': 'Repair'
    }
    return exact.get(key)


def load_magic_option_codes():
    global magic_option_codes, magic_option_records
    global magic_database_path, magic_database_identity
    character = get_character_data() or {}
    identity = (int(get_locale()), str(character.get('server') or ''))
    if magic_database_identity == identity:
        return bool(magic_option_codes)
    magic_database_identity = identity
    magic_option_codes = {}
    magic_option_records = []
    magic_database_path = active_database_path()
    if not magic_database_path:
        plugin_log('Active magic-option database could not be identified; using built-in layouts')
        return False
    connection = None
    try:
        connection = readonly_database(magic_database_path)
        for option_id, name, degree, items, display in connection.execute(
                'SELECT id,name,degree,items,display FROM magicoption'):
            canonical = canonical_magic_option(name, display)
            if canonical:
                record = {
                    'name': canonical, 'degree': int(degree or 0), 'items': str(items or '')
                }
                magic_option_codes[int(option_id)] = record
                magic_option_records.append(record)
        plugin_log('Loaded %d magic-option codes from active database %s' % (
            len(magic_option_codes), os.path.basename(magic_database_path)))
        return bool(magic_option_codes)
    except Exception as error:
        magic_option_codes = {}
        magic_option_records = []
        plugin_log('Could not load active magic-option database: %s' % error)
        return False
    finally:
        if connection:
            connection.close()


# ======================================================================
# Gorunum yardimcilari
# ======================================================================
def html_safe(value):
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def fixed_width_text(content, width):
    return ('<table width="{0}" cellspacing="0" cellpadding="0">'
            '<tr><td>{1}</td></tr></table>').format(width, content)


def bar_html(width, color):
    # Ince renkli cizgi. Bos hucre Qt'de ~22 px yuksekliginde cizildigi icin
    # icine 3 px'lik bir bosluk karakteri konur.
    return ('<table width="%d" cellspacing="0" cellpadding="0"><tr>'
            '<td bgcolor="%s"><span style="font-size:3px;">&nbsp;</span></td></tr></table>') % (width, color)


def panel_html(width, height, background, accent=None):
    # Arka plan karti: istege bagli ust vurgu seridi + govde.
    bar = ''
    if accent:
        bar = ('<tr><td bgcolor="%s"><span style="font-size:3px;">&nbsp;</span></td></tr>' % accent)
    return ('<table width="%d" height="%d" cellspacing="0" cellpadding="0" bgcolor="%s">'
            '%s<tr><td>&nbsp;</td></tr></table>') % (width, height, background, bar)


def progress_bar_html(ratio, width, color):
    ratio = max(0.0, min(1.0, float(ratio)))
    filled = int(width * ratio)
    rest = width - filled
    cells = ''
    if filled > 0:
        cells += '<td width="%d" height="8" bgcolor="%s"></td>' % (filled, color)
    if rest > 0:
        cells += '<td width="%d" height="8" bgcolor="%s"></td>' % (rest, BAR_EMPTY)
    return '<table width="%d" cellspacing="0" cellpadding="0"><tr>%s</tr></table>' % (width, cells)


def set_status(message, level='muted'):
    debug_write('STATUS %s' % message)
    color = LEVEL_DARK.get(level, LEVEL_DARK['muted'])
    QtBind.setText(gui, lbl_status, fixed_width_text(
        '<font color="%s"><b>%s</b></font>' % (color, html_safe(message)), 690))


def set_result(mode, message, level='muted'):
    debug_write('RESULT %s: %s' % (mode, message))
    states[mode]['last_result'] = message
    color = LEVEL_LIGHT.get(level, LEVEL_LIGHT['muted'])
    QtBind.setText(gui, result_labels[mode], fixed_width_text(
        '<font color="%s">%s</font>' % (color, html_safe(message)), 450))


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return '%d:%02d:%02d' % (hours, minutes, secs)
    return '%02d:%02d' % (minutes, secs)


# ======================================================================
# Esya siniflandirma
# ======================================================================
def item_degree(item_data):
    servername = str(item_data.get('servername') or '')
    for token in re.findall(r'(?:^|_)(\d{1,2})(?=_|$)', servername):
        degree = int(token)
        if 1 <= degree <= 15:
            return degree
    return None


def item_magic_categories(tid2, tid3):
    if tid2 == 6:
        return {'weapon'}
    if tid2 == 4:
        return {'shield'}
    if tid2 in (1, 2, 3, 9, 10, 11):
        categories = {'armor'}
        piece = {1: 'helm', 3: 'mail', 4: 'pants'}.get(tid3)
        if piece:
            categories.add(piece)
        return categories
    if tid2 in (5, 12):
        categories = {'accessory'}
        subtype = {1: 'earring', 2: 'necklace', 3: 'ring'}.get(tid3)
        if subtype:
            categories.add(subtype)
        return categories
    return set()


def database_available_stats(item_data, tid2, tid3):
    if not load_magic_option_codes():
        return []
    categories = item_magic_categories(tid2, tid3)
    if not categories:
        return []
    degree = item_degree(item_data)
    matching = []
    if degree is not None:
        matching = [record for record in magic_option_records if record['degree'] == degree]
    if not matching:
        matching = magic_option_records
    result = []
    for record in matching:
        option_categories = set(value.strip().lower() for value in record['items'].split(',') if value.strip())
        name = record['name']
        if categories.isdisjoint(option_categories) or name in IGNORED_RESPONSE_STATS:
            continue
        if name not in result:
            result.append(name)
    return result


def item_classification(item):
    try:
        data = get_item(int(item.get('model', 0)))
    except Exception:
        data = None
    if not data or int(data.get('tid1', 0)) != 1:
        return None
    tid2 = int(data.get('tid2', 0))
    tid3 = int(data.get('tid3', 0))
    if tid2 == 6 and tid3 in WEAPON_NAMES:
        fallback = list(WEAPON_STATS)
        return ('Weapon', WEAPON_NAMES[tid3], database_available_stats(data, tid2, tid3) or fallback)
    if tid2 == 4 and tid3 in (1, 2):
        fallback = list(SHIELD_STATS)
        return ('Shield', 'Chinese Shield' if tid3 == 1 else 'European Shield',
                database_available_stats(data, tid2, tid3) or fallback)
    if tid2 in (1, 2, 3, 9, 10, 11) and tid3 in ARMOR_STATS:
        family = {1: 'Garment', 2: 'Protector', 3: 'Armor', 9: 'Robe', 10: 'Light Armor', 11: 'Heavy Armor'}[tid2]
        fallback = list(ARMOR_STATS[tid3])
        return ('Armor', '%s %s' % (family, ARMOR_NAMES[tid3]),
                database_available_stats(data, tid2, tid3) or fallback)
    if tid2 in (5, 12) and tid3 in ACCESSORY_STATS:
        race = 'Chinese' if tid2 == 5 else 'European'
        fallback = list(ACCESSORY_STATS[tid3])
        return ('Accessory', '%s %s' % (race, ACCESSORY_NAMES[tid3]),
                database_available_stats(data, tid2, tid3) or fallback)
    return None


def inventory_snapshot(mode):
    inventory = get_inventory()
    if not inventory or 'items' not in inventory:
        return []
    result = []
    for slot, item in enumerate(inventory['items']):
        if slot < 13 or not item:
            continue
        classification = item_classification(item)
        if not classification:
            continue
        copied = dict(item)
        copied['slot'] = slot
        copied['subtype'] = classification[1]
        copied['available_stats'] = classification[2]
        result.append(copied)
    return result


def find_inventory_item(slot):
    inventory = get_inventory()
    items = inventory.get('items', []) if inventory else []
    return items[slot] if 0 <= slot < len(items) else None


def find_consumable_slot(mode):
    inventory = get_inventory()
    if not inventory or 'items' not in inventory:
        return None
    names = CONSUMABLE_NAMES[mode]
    for slot, item in enumerate(inventory['items']):
        item_name = str(item.get('name', '')) if item else ''
        if any(name in item_name for name in names):
            return slot
    return None


def wheel_quantity(mode):
    # Envanterdeki tum yigin sayilarinin toplami (ayni tekerlek birden fazla yerde olabilir).
    inventory = get_inventory()
    if not inventory or 'items' not in inventory:
        return 0
    names = CONSUMABLE_NAMES[mode]
    total = 0
    for item in inventory['items']:
        if item and any(name in str(item.get('name', '')) for name in names):
            try:
                total += int(item.get('quantity', 1))
            except Exception:
                total += 1
    return total


# ======================================================================
# Mevcut mavileri okuma (On kontrol) - phBot alanlari belgelenmemis, best effort
# ======================================================================
def canonical_stat(text):
    text = str(text or '')
    for pattern, name in STAT_ALIASES:
        if pattern.search(text):
            return name
    return None


def parse_blue_field(raw):
    if isinstance(raw, dict):
        entries = [{'name': key, 'value': value} for key, value in raw.items()]
    elif isinstance(raw, (list, tuple)):
        entries = raw
    else:
        return None
    result = []
    for entry in entries:
        if isinstance(entry, dict):
            name = entry.get('name') or entry.get('type') or entry.get('option')
            value = entry.get('value', entry.get('amount', entry.get('val', 0)))
        elif isinstance(entry, str):
            match = re.match(r'^\s*(.*?)\s*[:+]?\s*(-?\d+)\s*%?\s*$', entry)
            name = match.group(1) if match else entry
            value = match.group(2) if match else 0
        else:
            return None
        canonical = canonical_stat(name)
        if canonical is None:
            return None
        try:
            value = int(value)
        except Exception:
            value = 0
        result.append({'name': canonical, 'value': value})
    return result


def read_item_blues(live_item):
    # Donus: [{'name','value'}...] ya da phBot veriyi vermiyorsa None.
    if not live_item:
        return None
    for key in BLUE_FIELD_NAMES:
        raw = live_item.get(key)
        if raw:
            parsed = parse_blue_field(raw)
            if parsed is not None:
                return parsed
    return None


def target_reached_from_blues(mode, item, entries):
    if mode == 'fate':
        return len(entries) >= item.get('target', 1)
    counts = {}
    totals = {}
    for entry in entries:
        counts[entry['name']] = counts.get(entry['name'], 0) + 1
        totals[entry['name']] = totals.get(entry['name'], 0) + entry['value']
    counts['STR+INT'] = counts.get('STR', 0) + counts.get('INT', 0)
    totals['STR+INT'] = totals.get('STR', 0) + totals.get('INT', 0)
    if mode == 'fortune':
        checks = [counts.get(x['name'], 0) >= x['count'] for x in item.get('targets', [])]
        if not checks:
            return False
        return any(checks) if item.get('match', 'all') == 'any' else all(checks)
    checks = [totals.get(x['name'], 0) >= x['value'] for x in item.get('targets', [])]
    return bool(checks) and all(checks)


# ======================================================================
# Kalicilik (ayar + kuyruk), gecmis
# ======================================================================
def config_file():
    try:
        folder = get_config_dir()
    except Exception:
        folder = None
    if not folder:
        folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(folder, pName + '.json')


def history_file():
    return os.path.join(get_log_dir(), pName, pName + '_history.txt')


def clamp_int(value, low, high, default):
    try:
        number = int(value)
    except Exception:
        return default
    return max(low, min(high, number))


def sanitize_settings(raw):
    result = dict(DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return result
    for mode in MODES:
        key = 'delay_' + mode
        result[key] = clamp_int(raw.get(key), MIN_DELAY_MS[mode], MAX_DELAY_MS, DEFAULT_SETTINGS[key])
    result['next_item'] = clamp_int(raw.get('next_item'), 300, MAX_DELAY_MS, DEFAULT_SETTINGS['next_item'])
    result['timeout'] = clamp_int(raw.get('timeout'), 3, 120, DEFAULT_SETTINGS['timeout'])
    for key in ('jitter', 'confirm', 'precheck'):
        result[key] = bool(raw.get(key, DEFAULT_SETTINGS[key]))
    return result


def serialize_queue(mode):
    out = []
    for queued in states[mode]['queue']:
        entry = {'slot': queued['slot'], 'model': queued['model'], 'name': queued['name']}
        if mode == 'fate':
            entry['target'] = queued['target']
        else:
            entry['targets'] = [dict(value) for value in queued['targets']]
            if mode == 'fortune':
                entry['match'] = queued.get('match', 'all')
        out.append(entry)
    return out


def sanitize_entry(mode, raw):
    try:
        slot = int(raw['slot'])
        model = int(raw['model'])
        if not 0 <= slot <= 255:
            return None
        entry = {'slot': slot, 'model': model, 'name': str(raw.get('name', 'Unknown')),
                 'completed': False}
        if mode == 'fate':
            target = int(raw['target'])
            if not 1 <= target <= MAX_LINES:
                return None
            entry.update({'target': target, 'last_count': None})
            return entry
        key = 'count' if mode == 'fortune' else 'value'
        maximum = MAX_LINES if mode == 'fortune' else MAX_TARGET_VALUE
        targets = []
        for target in raw['targets']:
            name = str(target['name'])
            value = int(target[key])
            if not name or not 1 <= value <= maximum:
                return None
            targets.append({'name': name, key: value})
        if not targets:
            return None
        entry['targets'] = targets
        if mode == 'fortune':
            entry['match'] = 'any' if raw.get('match') == 'any' else 'all'
            entry['last_counts'] = None
        else:
            entry['totals'] = {}
        return entry
    except Exception:
        return None


def save_state(report=False):
    data = {'version': pVersion, 'settings': settings,
            'queues': dict((mode, serialize_queue(mode)) for mode in MODES)}
    try:
        path = config_file()
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        temporary = path + '.tmp'
        with open(temporary, 'w', encoding='utf-8') as output:
            json.dump(data, output, ensure_ascii=False, indent=1)
        os.replace(temporary, path)
        if report:
            set_status('Ayarlar ve kuyruklar kaydedildi', 'ok')
        return True
    except Exception as error:
        plugin_log('Kaydedilemedi: %s' % error)
        if report:
            set_status('Kaydedilemedi: %s' % error, 'err')
        return False


def load_state(report=False):
    global settings
    try:
        with open(config_file(), 'r', encoding='utf-8') as source:
            data = json.load(source)
    except IOError:
        if report:
            set_status('Kayıtlı ayar dosyası bulunamadı', 'warn')
        return False
    except Exception as error:
        plugin_log('Ayar dosyası okunamadı: %s' % error)
        if report:
            set_status('Ayar dosyası okunamadı', 'err')
        return False
    if active_mode is not None:
        if report:
            set_status('Yüklemeden önce çalışan işlemi durdur', 'warn')
        return False
    settings = sanitize_settings(data.get('settings'))
    restored = 0
    for mode in MODES:
        queue = []
        for raw in (data.get('queues') or {}).get(mode, []):
            entry = sanitize_entry(mode, raw)
            if entry:
                queue.append(entry)
        states[mode]['queue'][:] = queue
        states[mode]['index'] = 0
        restored += len(queue)
    sync_settings_widgets()
    refresh_all_queues()
    if report:
        set_status('Yüklendi: %d kuyruk öğesi' % restored, 'ok')
    return True


def history_add(mode, item, summary, reached, note=''):
    line = '%s | %-7s | slot %-3d | %s | %s%s%s' % (
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'), MODE_LABELS[mode], item['slot'],
        item.get('name', '?'), summary, ' | HEDEF' if reached else '',
        ' | %s' % note if note else '')
    with history_lock:
        history.appendleft(line)
        try:
            path = history_file()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'a', encoding='utf-8') as output:
                output.write(line + '\n')
        except Exception as error:
            plugin_log('Geçmiş dosyasına yazılamadı: %s' % error)
    refresh_history_list()


def refresh_history_list():
    try:
        QtBind.clear(gui, lst_history)
        with history_lock:
            for line in list(history):
                QtBind.append(gui, lst_history, line)
    except Exception:
        pass


def history_open_clicked():
    try:
        open_folder(os.path.dirname(history_file()))
        set_status('Geçmiş klasörü açıldı', 'ok')
    except Exception:
        set_status('Geçmiş klasörü açılamadı: Log/RWheelManager klasörüne bak', 'err')


def history_clear_clicked():
    with history_lock:
        history.clear()
    refresh_history_list()
    set_status('Liste temizlendi (dosyadaki kayıtlar silinmedi)', 'muted')


# ======================================================================
# Ayarlar sayfasi
# ======================================================================
def read_edit_int(widget, low, high, default):
    return clamp_int(QtBind.text(gui, widget).strip(), low, high, default)


def sync_settings_widgets():
    try:
        for mode in MODES:
            QtBind.setText(gui, delay_edits[mode], str(settings['delay_' + mode]))
        QtBind.setText(gui, edit_next, str(settings['next_item']))
        QtBind.setText(gui, edit_timeout, str(settings['timeout']))
        QtBind.setChecked(gui, chk_jitter, settings['jitter'])
        QtBind.setChecked(gui, chk_confirm, settings['confirm'])
        QtBind.setChecked(gui, chk_precheck, settings['precheck'])
    except Exception:
        pass


def settings_apply_clicked():
    raw = dict(settings)
    for mode in MODES:
        raw['delay_' + mode] = QtBind.text(gui, delay_edits[mode]).strip()
    raw['next_item'] = QtBind.text(gui, edit_next).strip()
    raw['timeout'] = QtBind.text(gui, edit_timeout).strip()
    settings.update(sanitize_settings(raw))
    sync_settings_widgets()
    if save_state():
        set_status('Ayarlar uygulandı ve kaydedildi (sınırlar: Fate/Fortune ≥300 ms, Pen ≥1500 ms)', 'ok')
    else:
        set_status('Ayarlar uygulandı fakat dosyaya kaydedilemedi', 'warn')


def settings_load_clicked():
    load_state(report=True)


def jitter_changed(checked):
    settings['jitter'] = bool(checked)
    save_state()


def confirm_changed(checked):
    settings['confirm'] = bool(checked)
    save_state()


def precheck_changed(checked):
    settings['precheck'] = bool(checked)
    save_state()


def mode_delay(mode):
    base = clamp_int(settings.get('delay_' + mode), MIN_DELAY_MS[mode], MAX_DELAY_MS,
                     DEFAULT_SETTINGS['delay_' + mode]) / 1000.0
    if settings.get('jitter'):
        base += random.uniform(0.0, 0.15)
    return base


def next_item_delay():
    base = clamp_int(settings.get('next_item'), 300, MAX_DELAY_MS, DEFAULT_SETTINGS['next_item']) / 1000.0
    if settings.get('jitter'):
        base += random.uniform(0.0, 0.15)
    return base


def response_timeout():
    return clamp_int(settings.get('timeout'), 3, 120, DEFAULT_SETTINGS['timeout'])


# ======================================================================
# Envanter / hedef arayuzu
# ======================================================================
def selected_item(mode):
    widget = inventory_lists[mode]
    index = QtBind.currentIndex(gui, widget)
    values = states[mode]['inventory']
    return values[index] if 0 <= index < len(values) else None


def format_item(item):
    return 'Slot %d | +%s | %s' % (item['slot'], item.get('plus', 0), item.get('name', 'Unknown'))


def refresh_inventory(mode):
    state = states[mode]
    state['inventory'] = inventory_snapshot(mode)
    QtBind.clear(gui, inventory_lists[mode])
    for item in state['inventory']:
        suffix = ' | %s' % item['subtype'] if mode == 'fortune' else ''
        QtBind.append(gui, inventory_lists[mode], format_item(item) + suffix)
    set_status('%s: envanterde %d uygun eşya bulundu' % (
        MODE_LABELS[mode], len(state['inventory'])),
        'ok' if state['inventory'] else 'warn')


def fate_refresh_inventory(): refresh_inventory('fate')
def fortune_refresh_inventory(): refresh_inventory('fortune')
def pen_refresh_inventory(): refresh_inventory('pen')


def inspect_item(mode):
    state = states[mode]
    item = selected_item(mode)
    if not item:
        set_status('Önce listeden bir eşya seç', 'warn')
        return
    state['selected'] = {'slot': item['slot'], 'model': item['model']}
    live = find_inventory_item(item['slot']) or {}
    debug_write('ITEM_DICT ' + json.dumps(live, default=str, ensure_ascii=True, sort_keys=True))
    blues = read_item_blues(live)
    if blues is None:
        note = 'mavi verisi okunamadı'
    else:
        note = 'mevcut mavi: %d satır' % len(blues)
    QtBind.setText(gui, selected_labels[mode], fixed_width_text(
        '<font color="%s"><b>%s</b></font><br><font color="%s">%s</font>' % (
            PAPER_TEXT, html_safe(format_item(item)), PAPER_MUTED, html_safe(note)), 350))
    if mode in ('fortune', 'pen'):
        state['available'] = list(item['available_stats'])
        if all(name in state['available'] for name in ('STR', 'INT')):
            state['available'].insert(state['available'].index('INT') + 1, 'STR+INT')
        state['targets'] = []
        QtBind.clear(gui, stat_lists[mode])
        QtBind.clear(gui, target_lists[mode])
        for name in state['available']:
            QtBind.append(gui, stat_lists[mode], name)
    set_status('%s: eşya seçildi, hedefini ayarla' % MODE_LABELS[mode], 'muted')


def fate_inspect(): inspect_item('fate')
def fortune_inspect(): inspect_item('fortune')
def pen_inspect(): inspect_item('pen')


def refresh_targets(mode):
    QtBind.clear(gui, target_lists[mode])
    for target in states[mode]['targets']:
        if mode == 'fortune':
            text = '%s x%d' % (target['name'], target['count'])
        else:
            text = '%s >= %d toplam' % (target['name'], target['value'])
        QtBind.append(gui, target_lists[mode], text)


def add_stat_target(mode):
    name = QtBind.text(gui, stat_lists[mode])
    if not name:
        set_status('Önce soldaki listeden bir stat seç', 'warn')
        return
    try:
        value = int(QtBind.text(gui, target_inputs[mode]).strip())
    except Exception:
        value = 0
    maximum = MAX_LINES if mode == 'fortune' else MAX_TARGET_VALUE
    if value < 1 or value > maximum:
        set_status('Hedef değeri izin verilen aralığın dışında', 'err')
        return
    key = 'count' if mode == 'fortune' else 'value'
    for target in states[mode]['targets']:
        if target['name'] == name:
            target[key] = value
            refresh_targets(mode)
            set_status('Hedef güncellendi: %s' % name, 'ok')
            return
    states[mode]['targets'].append({'name': name, key: value})
    refresh_targets(mode)
    set_status('Hedef eklendi: %s' % name, 'ok')


def fortune_add_target(): add_stat_target('fortune')
def pen_add_target(): add_stat_target('pen')


def remove_stat_target(mode):
    index = QtBind.currentIndex(gui, target_lists[mode])
    if index < 0 or index >= len(states[mode]['targets']):
        set_status('Silinecek hedefi seç', 'warn')
        return
    removed = states[mode]['targets'].pop(index)
    refresh_targets(mode)
    set_status('%s hedefi silindi' % removed['name'], 'muted')


def fortune_remove_target(): remove_stat_target('fortune')
def pen_remove_target(): remove_stat_target('pen')


def queue_item(mode):
    state = states[mode]
    item = selected_item(mode)
    if not item:
        set_status('Önce listeden bir eşya seç', 'warn')
        return
    if mode != 'fate':
        chosen = state.get('selected')
        if not chosen or chosen['slot'] != item['slot'] or chosen['model'] != item['model']:
            set_status('Kuyruğa eklemeden önce bu eşya için "Seç"e bas', 'warn')
            return
    queued = {
        'slot': item['slot'], 'model': item['model'],
        'name': item.get('name', 'Unknown'), 'completed': False
    }
    if mode == 'fate':
        try:
            target = int(QtBind.text(gui, target_inputs[mode]).strip())
        except Exception:
            target = 0
        if target < 1 or target > MAX_LINES:
            set_status('Mavi satır hedefi 1 ile 32 arasında olmalı', 'err')
            return
        queued.update({'target': target, 'last_count': None})
    else:
        if not state['targets']:
            set_status('En az bir stat hedefi ekle', 'warn')
            return
        queued['targets'] = [dict(value) for value in state['targets']]
        if mode == 'fortune':
            match_index = QtBind.currentIndex(gui, match_logic_widgets[mode])
            queued['match'] = 'any' if match_index == 1 else 'all'
            queued['last_counts'] = None
        if mode == 'pen':
            queued['totals'] = {}
    for index, existing in enumerate(state['queue']):
        if existing['slot'] == queued['slot']:
            state['queue'][index] = queued
            refresh_queue(mode)
            save_state()
            set_status('%s kuyruğundaki hedef güncellendi' % MODE_LABELS[mode], 'ok')
            return
    state['queue'].append(queued)
    refresh_queue(mode)
    save_state()
    set_status('Eşya %s kuyruğuna eklendi' % MODE_LABELS[mode], 'ok')


def fate_queue_item(): queue_item('fate')
def fortune_queue_item(): queue_item('fortune')
def pen_queue_item(): queue_item('pen')


def target_summary(mode, item):
    if mode == 'fate':
        current = '?' if item['last_count'] is None else item['last_count']
        return 'mavi %s/%d' % (current, item['target'])
    if mode == 'fortune':
        logic = 'HEPSİ' if item.get('match', 'all') == 'all' else 'HERHANGİ'
        return '%s: %s' % (logic, ', '.join(
            '%s x%d' % (x['name'], x['count']) for x in item['targets']))
    return ', '.join('%s %s/%d' % (
        x['name'], item['totals'].get(x['name'], '?'), x['value']) for x in item['targets'])


def refresh_queue(mode):
    QtBind.clear(gui, queue_lists[mode])
    state = states[mode]
    for index, item in enumerate(state['queue']):
        if item.get('completed', False):
            marker = u'✓'
        elif active_mode == mode and index == state['index']:
            marker = '>'
        else:
            marker = ' '
        QtBind.append(gui, queue_lists[mode], '%s Slot %d | %s | %s' % (
            marker, item['slot'], target_summary(mode, item), item['name']))
    render_dashboard(mode)


def remove_queue_item(mode):
    if active_mode is not None:
        set_status('Kuyruğu düzenlemeden önce çalışan işlemi durdur', 'warn')
        return
    index = QtBind.currentIndex(gui, queue_lists[mode])
    if index < 0 or index >= len(states[mode]['queue']):
        set_status('Önce kuyruktan bir öğe seç', 'warn')
        return
    del states[mode]['queue'][index]
    refresh_queue(mode)
    save_state()
    set_status('Öğe kuyruktan çıkarıldı', 'muted')


def clear_queue(mode):
    if active_mode is not None:
        set_status('Kuyruğu temizlemeden önce çalışan işlemi durdur', 'warn')
        return
    states[mode]['queue'][:] = []
    refresh_queue(mode)
    save_state()
    set_status('%s kuyruğu temizlendi' % MODE_LABELS[mode], 'muted')


def fate_remove_queue(): remove_queue_item('fate')
def fortune_remove_queue(): remove_queue_item('fortune')
def pen_remove_queue(): remove_queue_item('pen')
def fate_clear_queue(): clear_queue('fate')
def fortune_clear_queue(): clear_queue('fortune')
def pen_clear_queue(): clear_queue('pen')


# ======================================================================
# Canli durum paneli
# ======================================================================
def item_progress(mode, item):
    if not item:
        return 0.0
    if mode == 'fate':
        last = item.get('last_count')
        return 0.0 if last is None else min(1.0, float(last) / max(1, item.get('target', 1)))
    if mode == 'fortune':
        counts = item.get('last_counts')
        targets = item.get('targets') or []
        if not counts or not targets:
            return 0.0
        ratios = [min(1.0, float(counts.get(x['name'], 0)) / x['count']) for x in targets]
        return max(ratios) if item.get('match') == 'any' else sum(ratios) / len(ratios)
    totals = item.get('totals') or {}
    targets = item.get('targets') or []
    if not totals or not targets:
        return 0.0
    ratios = [min(1.0, float(totals.get(x['name'], 0)) / x['value']) for x in targets]
    return sum(ratios) / len(ratios)


def render_dashboard(mode):
    try:
        label = dashboard_labels[mode]
    except Exception:
        return
    state = states[mode]
    record = stats[mode]
    running = active_mode == mode
    now = time.time()
    elapsed = 0
    if record['started']:
        elapsed = (record['ended'] or now) - record['started']
    queue = state['queue']
    done = sum(1 for queued in queue if queued.get('completed'))
    current = None
    if running and 0 <= state['index'] < len(queue):
        current = queue[state['index']]
    elif queue:
        pending = next_pending_index(mode)
        current = queue[pending] if pending is not None else queue[-1]
    ratio = item_progress(mode, current)
    left = wheel_quantity(mode)
    accent = ACCENT[mode]
    if running:
        status = '<font color="%s"><b>● ÇALIŞIYOR</b></font>' % LEVEL_DARK['ok']
    else:
        status = '<font color="%s"><b>■ BEKLEMEDE</b></font>' % DARK_MUTED
    start_wheels = record['wheels_start']
    used = ' <font color="%s">(kullanılan %d)</font>' % (DARK_MUTED, max(0, start_wheels - left)) \
        if start_wheels is not None else ''
    name = html_safe(current['name']) if current else '-'
    slot = ('Slot %d' % current['slot']) if current else ''
    html = (
        '<table width="218" height="204" cellspacing="0" cellpadding="8" bgcolor="%s"><tr><td valign="top">'
        '<font color="%s"><b>CANLI DURUM</b></font><br>%s<br>'
        '<font color="%s">Roll sayısı</font> <font color="#ffffff"><b>%d</b></font><br>'
        '<font color="%s">Süre</font> <font color="#ffffff"><b>%s</b></font><br>'
        '<font color="%s">Kalan tekerlek</font> <font color="#ffffff"><b>%d</b></font>%s<br>'
        '<font color="%s">Kuyruk</font> <font color="#ffffff"><b>%d / %d</b></font><br><br>'
        '<font color="%s">%s</font> <font color="#ffffff">%s</font> <font color="%s">%%%d</font><br>%s<br><br>'
        '<font color="%s">En iyi:</font> <font color="#ffffff">%s</font>'
        '</td></tr></table>'
    ) % (CARD_DARK, GOLD, status,
         DARK_MUTED, record['rolls'],
         DARK_MUTED, format_duration(elapsed),
         DARK_MUTED, left, used,
         DARK_MUTED, done, len(queue),
         DARK_MUTED, slot, name, DARK_MUTED, int(ratio * 100), progress_bar_html(ratio, 196, accent),
         DARK_MUTED, html_safe(record['best_text']))
    QtBind.setText(gui, label, html)


def event_loop():
    global last_dash_refresh
    if active_mode is None:
        return
    now = time.time()
    if now - last_dash_refresh >= 1.0 and visible_page == 'queue' and visible_mode == active_mode:
        last_dash_refresh = now
        render_dashboard(active_mode)


# ======================================================================
# Zamanlayicilar ve istek dongusu
# ======================================================================
def cancel_timeout():
    global timeout_timer
    if timeout_timer:
        try:
            timeout_timer.cancel()
        except Exception:
            pass
    timeout_timer = None


def invalidate_timer():
    global pending_timer, timer_token, awaiting_response
    timer_token += 1
    awaiting_response = False
    if pending_timer:
        try:
            pending_timer.cancel()
        except Exception:
            pass
    pending_timer = None
    cancel_timeout()


def schedule_request(delay, mode):
    global pending_timer
    token = timer_token
    def callback():
        if active_mode == mode and token == timer_token:
            try:
                send_request(mode)
            except Exception as error:
                plugin_log('Request error: %s' % error)
                stop_operation('İstek gönderilemedi; işlem durduruldu', 'err')
    pending_timer = Timer(delay, callback)
    pending_timer.daemon = True
    pending_timer.start()


def start_timeout(mode):
    # Sunucu cevap vermezse otomasyonu durdurur; sessizce takili kalmaz.
    global timeout_timer, request_id
    cancel_timeout()
    request_id += 1
    current = request_id
    limit = response_timeout()
    def callback():
        if active_mode == mode and awaiting_response and current == request_id:
            debug_write('TIMEOUT waiting for 0xB151')
            stop_operation('Sunucudan %d sn cevap gelmedi; işlem durduruldu' % limit, 'err')
    timeout_timer = Timer(limit, callback)
    timeout_timer.daemon = True
    timeout_timer.start()


def active_item(mode):
    if single_roll and test_items.get(mode):
        return test_items[mode]
    state = states[mode]
    return state['queue'][state['index']] if 0 <= state['index'] < len(state['queue']) else None


def next_pending_index(mode, start=0):
    queue = states[mode]['queue']
    for index in range(max(0, start), len(queue)):
        if not queue[index].get('completed', False):
            return index
    return None


def send_request(mode):
    global awaiting_response
    if active_mode != mode or awaiting_response:
        return
    item = active_item(mode)
    if not item:
        stop_operation('Tüm %s hedeflerine ulaşıldı' % MODE_LABELS[mode], 'ok')
        return
    live = find_inventory_item(item['slot'])
    if not live or live.get('model') != item['model']:
        stop_operation('Slot %d\'deki eşya değişmiş veya yerinden oynamış' % item['slot'], 'err')
        return
    consumable_slot = find_consumable_slot(mode)
    if consumable_slot is None:
        stop_operation('%s tekerleği/kalemi envanterde bulunamadı' % MODE_LABELS[mode], 'err')
        return
    if item['slot'] > 255 or consumable_slot > 255:
        stop_operation('Envanter slotu paket aralığının dışında', 'err')
        return
    awaiting_response = True
    request = b'\x02\x19\x02' + bytes([item['slot'], consumable_slot])
    debug_packet('TX', OPCODE_REQUEST, request, 'plugin')
    inject_joymax(OPCODE_REQUEST, request, False)
    start_timeout(mode)
    set_status('%s: slot %d roll ediliyor...' % (MODE_LABELS[mode], item['slot']), 'warn')


def precheck_queue(mode):
    # Mavileri okunabilen ve hedefe zaten ulasmis eşyalari roll atmadan isaretler.
    # Donus: (hedefte olanlarin sayisi, veri okunamayan eşya sayisi)
    reached = 0
    unreadable = 0
    for queued in states[mode]['queue']:
        if queued.get('completed', False):
            continue
        blues = read_item_blues(find_inventory_item(queued['slot']))
        if blues is None:
            unreadable += 1
            continue
        if target_reached_from_blues(mode, queued, blues):
            queued['completed'] = True
            reached += 1
            history_add(mode, queued, 'zaten hedefte (%d mavi satır okundu)' % len(blues),
                        True, 'ön kontrol, roll atılmadı')
    return reached, unreadable


def start_mode(mode, scripted=False):
    global active_mode, single_roll
    if active_mode is not None:
        set_status('%s işlemi zaten çalışıyor' % MODE_LABELS[active_mode], 'warn')
        return False
    state = states[mode]
    if not state['queue']:
        set_status('%s kuyruğuna en az bir eşya ekle' % MODE_LABELS[mode], 'warn')
        return False
    unreadable = 0
    if settings.get('precheck'):
        reached, unreadable = precheck_queue(mode)
        if reached:
            refresh_queue(mode)
            save_state()
    pending_index = next_pending_index(mode)
    if pending_index is None:
        set_status('%s kuyruğundaki tüm eşyalar zaten hedefte' % MODE_LABELS[mode], 'ok')
        refresh_queue(mode)
        return False
    for item in state['queue']:
        if item.get('completed', False):
            continue
        live = find_inventory_item(item['slot'])
        if not live or live.get('model') != item['model']:
            set_status('Kuyruktaki eşya slot %d\'de değişmiş' % item['slot'], 'err')
            return False
    if find_consumable_slot(mode) is None:
        set_status('%s tekerleği/kalemi envanterde bulunamadı' % MODE_LABELS[mode], 'err')
        return False
    if settings.get('confirm') and not scripted:
        now = time.time()
        if not (armed['mode'] == mode and now < armed['until']):
            armed['mode'] = mode
            armed['until'] = now + 10.0
            extra = ' (mevcut mavi verisi okunamadı)' if unreadable else ''
            set_status('⚠ Roll mevcut mavileri değiştirir%s. Onaylamak için 10 sn içinde tekrar BAŞLAT\'a bas' % extra, 'warn')
            return False
    armed['mode'] = None
    state['index'] = pending_index
    active_mode = mode
    single_roll = False
    invalidate_timer()
    record = new_stats()
    record['started'] = time.time()
    record['wheels_start'] = wheel_quantity(mode)
    stats[mode] = record
    refresh_all_queues()
    set_status('%s otomasyonu başladı' % MODE_LABELS[mode], 'ok')
    send_request(mode)
    return True


def test_mode(mode):
    global active_mode, single_roll
    if active_mode is not None:
        set_status('%s işlemi zaten çalışıyor' % MODE_LABELS[active_mode], 'warn')
        return
    item = selected_item(mode)
    if not item:
        set_status('Önce listeden bir eşya seç', 'warn')
        return
    test_items[mode] = {
        'slot': item['slot'], 'model': item['model'], 'name': item.get('name', 'Unknown'),
        'target': 1, 'last_count': None, 'targets': [], 'totals': {}
    }
    active_mode = mode
    single_roll = True
    invalidate_timer()
    send_request(mode)
    if active_mode == mode and awaiting_response:
        set_status('Tek roll (%s) gönderildi; cevap bekleniyor...' % MODE_LABELS[mode], 'warn')


def fate_start(): start_mode('fate')
def fortune_start(): start_mode('fortune')
def pen_start(): start_mode('pen')
def fate_test(): test_mode('fate')
def fortune_test(): test_mode('fortune')
def pen_test(): test_mode('pen')


def stop_operation(message='İşlem durduruldu', level='warn'):
    global active_mode, single_roll
    old_mode = active_mode
    if old_mode:
        test_items[old_mode] = None
        if stats[old_mode]['started'] and not stats[old_mode]['ended']:
            stats[old_mode]['ended'] = time.time()
    active_mode = None
    single_roll = False
    invalidate_timer()
    if old_mode:
        refresh_queue(old_mode)
    set_status(message, level)


def stop_clicked():
    if active_mode is None:
        set_status('Çalışan bir işlem yok', 'muted')
    else:
        stop_operation()


# ======================================================================
# Paket cozumleyiciler
# ======================================================================
def extended_option_section(data):
    # Newer item layout (seen on Hebe, iSRO): the item header is 8 bytes longer,
    # the option count sits at byte 34 and the records start at byte 35.
    # There is no leading metadata record, so every record is a real option.
    # Layout: [count][count * (uint32 id, uint32 value)][8 byte trailer].
    # Validated strictly (exact length, record shape) so legacy packets, whose
    # byte 34 is the 0x40 end of the metadata record, are never mistaken for it.
    if len(data) < 43 or data[0] != 1 or data[2] != 1:
        return None
    count = data[34]
    if count < 1 or count > MAX_LINES or len(data) != 43 + count * 8:
        return None
    for index in range(count):
        group = data[35 + index * 8:43 + index * 8]
        if group[0] == 0 or group[2] != 0 or group[3] != 0:
            return None
    return 35, count


def extended_classic_options(data, section, item=None):
    # Resolve extended-layout records without a database: the low byte of the
    # id is the classic stat code (id 0x023B -> 0x3B), the value is 32 bit.
    classification = None
    if item is not None:
        live_item = find_inventory_item(item['slot'])
        classification = item_classification(live_item) if live_item else None
    start, count = section
    options = []
    for index in range(count):
        group = data[start + index * 8:start + (index + 1) * 8]
        code = struct.unpack_from('<I', group, 0)[0]
        value = struct.unpack_from('<I', group, 4)[0]
        name = None
        if (code >> 8) == 2:
            low = code & 0xFF
            name = CLASSIC_CODES.get(low)
            if classification and classification[0] == 'Weapon':
                name = WEAPON_CONTEXT_CODES.get(low, name)
        options.append({'name': name or 'Unknown code 0x%08X' % code,
                        'value': value, 'code': code, 'format': 'extended'})
    return options


def fate_failure_reason(data, slot, parsed):
    if len(data) < 43:
        return 'paket çok kısa: %d bayt' % len(data)
    if data[0] != 1:
        return 'sunucu başarı bildirmedi, ilk bayt 0x%02X' % data[0]
    if data[2] != 1:
        return 'beklenmeyen tür baytı 0x%02X' % data[2]
    if parsed and parsed[0] != slot:
        return 'cevaptaki slot %d, beklenen %d' % (parsed[0], slot)
    if data[26] < 1 or data[26] > MAX_LINES + 1:
        return 'beklenmeyen seçenek sayısı %d' % data[26]
    return 'bilinmeyen paket düzeni'


def parse_fate(data):
    if len(data) < 43 or data[0] != 1 or data[2] != 1:
        return None
    section = extended_option_section(data)
    if section:
        return data[4], section[1]
    count = data[26]
    if count < 1 or count > MAX_LINES + 1:
        return None
    blue_count = count - 1
    return (data[4], blue_count) if len(data) >= 43 + blue_count * 8 else None


def parse_fortune(data, item=None):
    # vSRO responses contain a complete option record section at offset 27:
    # optionCount at 26, followed by [uint32 magicOptionID][uint32 value].
    # Resolve those IDs from the database selected by phBot for the active server.
    section = extended_option_section(data)
    if section and item is not None and data[4] == item['slot'] and not magic_option_codes:
        load_magic_option_codes()
    if section and item is not None and data[4] == item['slot'] and not magic_option_codes:
        return extended_classic_options(data, section, item)
    if (item is not None and len(data) >= 35 and data[0] == 1 and data[2] == 1 and
            data[4] == item['slot'] and load_magic_option_codes()):
        if section:
            records_start, count = section
        else:
            count = data[26]
            records_start = 27
        records_end = records_start + count * 8
        if 1 <= count <= MAX_LINES + 1 and records_end <= len(data):
            options = []
            for index in range(count):
                group = data[records_start + index * 8:records_start + (index + 1) * 8]
                # Verified leading metadata record in Fortune responses.
                # Match its full bytes and position; unknown stat IDs elsewhere
                # must still pass through the normal safety validation.
                if index == 0 and group == b'\x01\x02\x00\x00\x00\x00\x00\x40':
                    continue
                code = struct.unpack_from('<I', group, 0)[0]
                value = struct.unpack_from('<I', group, 4)[0]
                if code == 0:
                    continue
                option = magic_option_codes.get(code)
                options.append({
                    'name': option['name'] if option else 'Unknown code 0x%08X' % code,
                    'value': value, 'code': code, 'format': 'active-db'
                })
            if options:
                return options
    classification = None
    if item is not None:
        live_item = find_inventory_item(item['slot'])
        classification = item_classification(live_item) if live_item else None
    candidates = []
    for start in range(max(0, len(data) - 7)):
        cursor = start
        options = []
        while cursor + 8 <= len(data):
            group = data[cursor:cursor + 8]
            if (group[0] == 0 or group[1] != 2 or group[2] != 0 or group[3] != 0 or
                    group[4] == 0 or group[5] != 0 or group[6] != 0 or group[7] != 0):
                break
            name = CLASSIC_CODES.get(group[0])
            if classification and classification[0] == 'Weapon':
                name = WEAPON_CONTEXT_CODES.get(group[0], name)
            options.append({'name': name or 'Unknown code 0x%02X' % group[0],
                            'value': group[4]})
            cursor += 8
        if options:
            candidates.append((start, options))
    if candidates:
        candidates.sort(key=lambda entry: (-len(entry[1]), entry[0]))
        return candidates[0][1]
    if len(data) >= 35:
        options = []
        for index in range(len(data[35:]) // 8):
            group = data[35 + index * 8:43 + index * 8]
            code = struct.unpack_from('<I', group, 0)[0]
            if code in DG12_CODES:
                options.append({'name': DG12_CODES[code], 'value': struct.unpack_from('<I', group, 4)[0]})
        return options
    return []


def normalize_fortune_options(item, options):
    classification = item_classification(find_inventory_item(item['slot']))
    if not classification:
        return False, 'Eşya sınıflandırılamadı'
    available = classification[2]
    for option in options:
        if option['name'] == 'Block Rate' and 'Evade Block' in available:
            option['name'] = 'Evade Block'
        elif option['name'] == 'Block Rate' and 'Block' in available:
            option['name'] = 'Block'
    invalid = sorted(set(option['name'] for option in options
                         if option['name'] not in available and option['name'] not in IGNORED_RESPONSE_STATS))
    if invalid:
        return False, 'Bu eşyada olamayacak stat(lar): %s' % ', '.join(invalid)
    return True, ''


def parse_pen(data, item=None):
    if len(data) < 14 or data[:4] != b'\x01\x02\x01\x02':
        return None
    length = struct.unpack_from('<H', data, 4)[0]
    key_end = 6 + length
    item_start = key_end + 8  # uint32 old value + uint32 new value
    if length < 1 or item_start + 31 > len(data):
        return None
    count_position = item_start + 22
    internal_position = item_start + 30
    records_start = item_start + 31
    count = data[count_position]
    visible = count - 1
    if count < 2 or visible > MAX_LINES or data[internal_position] != 0x40:
        return None
    if records_start + visible * 8 > len(data):
        return None
    # Server-specific Pen responses can use the active database's full uint32
    # magic-option IDs, followed by uint32 values, just like Fortune records.
    if item is not None and load_magic_option_codes():
        totals = {}
        valid = True
        for index in range(visible):
            group = data[records_start + index * 8:records_start + (index + 1) * 8]
            code = struct.unpack_from('<I', group, 0)[0]
            value = struct.unpack_from('<I', group, 4)[0]
            option = magic_option_codes.get(code)
            if not option or value <= 0:
                valid = False
                break
            totals[option['name']] = totals.get(option['name'], 0) + value
        if valid and totals:
            classification = item_classification(find_inventory_item(item['slot']))
            available = classification[2] if classification else []
            invalid = [name for name in totals if
                       name not in available and name not in IGNORED_RESPONSE_STATS]
            if not invalid:
                return data[item_start], totals
    totals = {}
    for index in range(visible):
        group = data[records_start + index * 8:records_start + (index + 1) * 8]
        if (group[1] != 2 or group[2] != 0 or group[3] != 0 or group[4] == 0 or
                group[5] != 0 or group[6] != 0 or group[7] != 0):
            return None
        name = PEN_STAT_CODES.get(group[0])
        if not name:
            return None
        totals[name] = totals.get(name, 0) + group[4]
    return data[item_start], totals


def record_roll(mode, item, summary, reached):
    record = stats[mode]
    record['rolls'] += 1
    ratio = 1.0 if reached else item_progress(mode, item)
    if record['best'] is None or ratio > record['best']:
        record['best'] = ratio
        record['best_text'] = summary
    history_add(mode, item, summary, reached, 'tek roll testi' if single_roll else '')


def process_response(data):
    global awaiting_response, single_roll
    mode = active_mode
    if not mode or not awaiting_response:
        return
    awaiting_response = False
    cancel_timeout()
    item = active_item(mode)
    if not item:
        stop_operation('Aktif eşya yok; işlem durduruldu', 'err')
        return
    reached = False
    if mode == 'fate':
        parsed = parse_fate(data)
        if not parsed or parsed[0] != item['slot']:
            raw = ' '.join('%02X' % value for value in data[:64])
            reason = fate_failure_reason(data, item['slot'], parsed)
            plugin_log('Fate unverified 0xB151 (%d bytes): %s%s' % (
                len(data), raw, ' ...' if len(data) > 64 else ''))
            debug_write('Fate unverified 0xB151 raw (%d bytes): %s%s' % (
                len(data), ' '.join('%02X' % value for value in data[:512]),
                ' ...' if len(data) > 512 else ''))
            stop_operation('Fate cevabı doğrulanamadı (%s)' % reason, 'err')
            set_result(mode, 'Paket %d bayt: %s%s' % (
                len(data), raw[:96], ' ...' if len(raw) > 96 else ''), 'err')
            return
        item['last_count'] = parsed[1]
        reached = parsed[1] >= item.get('target', 1)
        summary = '%d mavi satır' % parsed[1]
        set_result(mode, 'Slot %d: %d mavi satır' % (item['slot'], parsed[1]), 'ok')
    elif mode == 'fortune':
        options = parse_fortune(data, item)
        if not options:
            debug_write('Fortune unverified 0xB151 raw (%d bytes): %s%s' % (
                len(data), ' '.join('%02X' % value for value in data[:512]),
                ' ...' if len(data) > 512 else ''))
            stop_operation('Fortune cevabında doğrulanmış stat bulunamadı', 'err')
            return
        valid, reason = normalize_fortune_options(item, options)
        if not valid:
            debug_write('Fortune unsafe layout 0xB151 raw (%d bytes): %s%s' % (
                len(data), ' '.join('%02X' % value for value in data[:512]),
                ' ...' if len(data) > 512 else ''))
            stop_operation(reason, 'err')
            return
        counts = {}
        for option in options:
            counts[option['name']] = counts.get(option['name'], 0) + 1
        if any(target['name'] == 'STR+INT' for target in item.get('targets', [])):
            counts['STR+INT'] = counts.get('STR', 0) + counts.get('INT', 0)
        item['last_counts'] = dict(counts)
        target_checks = [counts.get(x['name'], 0) >= x['count']
                         for x in item.get('targets', [])]
        if item.get('match', 'all') == 'any':
            reached = any(target_checks)
        else:
            reached = all(target_checks)
        summary = ', '.join('%s x%d' % pair for pair in sorted(counts.items()))
        set_result(mode, summary, 'ok')
    else:
        parsed = parse_pen(data, item)
        if not parsed or parsed[0] != item['slot']:
            debug_write('Pen unverified 0xB151 raw (%d bytes): %s%s' % (
                len(data), ' '.join('%02X' % value for value in data[:512]),
                ' ...' if len(data) > 512 else ''))
            stop_operation('Pen cevabı doğrulanamadı', 'err')
            return
        item['totals'] = parsed[1]
        if any(target['name'] == 'STR+INT' for target in item.get('targets', [])):
            item['totals']['STR+INT'] = parsed[1].get('STR', 0) + parsed[1].get('INT', 0)
        reached = all(parsed[1].get(x['name'], 0) >= x['value'] for x in item.get('targets', []))
        summary = ', '.join('%s=%d' % pair for pair in sorted(parsed[1].items()))
        set_result(mode, summary, 'ok')
    plugin_log('%s slot %d response processed' % (MODE_LABELS[mode], item['slot']))
    record_roll(mode, item, summary, reached)
    if single_roll:
        single_roll = False
        stop_operation('Tek roll testi (%s) tamamlandı' % MODE_LABELS[mode], 'ok')
        return
    if reached:
        item['completed'] = True
        next_index = next_pending_index(mode, states[mode]['index'] + 1)
        refresh_queue(mode)
        if next_index is None:
            stop_operation('Tüm %s hedeflerine ulaşıldı' % MODE_LABELS[mode], 'ok')
        else:
            states[mode]['index'] = next_index
            refresh_queue(mode)
            schedule_request(next_item_delay(), mode)
    else:
        refresh_queue(mode)
        schedule_request(mode_delay(mode), mode)


# ======================================================================
# phBot olaylari ve script komutu
# ======================================================================
def handle_silkroad(opcode, data):
    if opcode == OPCODE_REQUEST:
        debug_packet('TX', opcode, data, 'client-hook')
    return True


def handle_joymax(opcode, data):
    if opcode == OPCODE_RESPONSE:
        debug_packet('RX', opcode, data, 'server')
    try:
        if opcode == OPCODE_RESPONSE and active_mode is not None:
            process_response(data)
    except Exception as error:
        plugin_log('Packet processing error for 0x%04X: %s' % (opcode, error))
        if opcode == OPCODE_RESPONSE and active_mode is not None:
            stop_operation('Paket işlenemedi; işlem durduruldu', 'err')
    return True


def disconnected():
    if active_mode is not None or awaiting_response:
        stop_operation('Bağlantı koptu; işlem durduruldu', 'err')
    else:
        invalidate_timer()
        set_status('Bağlantı koptu', 'muted')


def RWheel(args):
    # Script komutu: RWheel,fate | RWheel,fortune | RWheel,pen | RWheel,stop
    # Kayıtlı kuyruğu başlatır ve hemen döner; bitişi beklemek için script'e wait ekle.
    # phBot'un eklenti komutlarını çağırma biçimi canlıda doğrulanmadı.
    action = None
    for argument in (args or []):
        value = str(argument).strip().lower()
        if value in MODES or value == 'stop':
            action = value
            break
    if action is None:
        return {'success': False, 'message': 'RWheel: fate, fortune, pen veya stop yaz'}
    if action == 'stop':
        stop_operation('Script komutuyla durduruldu')
        return {'success': True, 'message': 'RWheel durduruldu'}
    started = start_mode(action, scripted=True)
    return {'success': bool(started), 'message': 'RWheel %s %s' % (
        action, 'başladı' if started else 'başlatılamadı (durum çubuğuna bak)')}


# ======================================================================
# Sayfa gecisleri
# ======================================================================
def move_widgets(widgets, visible):
    for widget, x, y in widgets:
        QtBind.move(gui, widget, x if visible else OFFSCREEN_X, y)


def show_view(mode, page='setup'):
    global visible_mode, visible_page
    visible_mode = mode
    visible_page = page
    for current_mode in MODES:
        move_widgets(setup_widgets[current_mode], page == 'setup' and current_mode == mode)
        move_widgets(queue_widgets[current_mode], page == 'queue' and current_mode == mode)
    move_widgets(history_widgets, page == 'history')
    move_widgets(settings_widgets, page == 'settings')
    mode_x, mode_w = MODE_TAB_BOX[mode]
    page_x, page_w = PAGE_TAB_BOX[page]
    QtBind.move(gui, mode_bar, mode_x, 64)
    QtBind.setText(gui, mode_bar, bar_html(mode_w, ACCENT[mode]))
    QtBind.move(gui, page_bar, page_x, 64)
    QtBind.setText(gui, page_bar, bar_html(page_w, GOLD))
    refresh_queue(mode)


def show_fate(): show_view('fate', visible_page if visible_page in ('setup', 'queue') else 'setup')
def show_fortune(): show_view('fortune', visible_page if visible_page in ('setup', 'queue') else 'setup')
def show_pen(): show_view('pen', visible_page if visible_page in ('setup', 'queue') else 'setup')
def page_setup(): show_view(visible_mode, 'setup')
def page_queue(): show_view(visible_mode, 'queue')
def page_history(): show_view(visible_mode, 'history')
def page_settings(): show_view(visible_mode, 'settings')


def refresh_all_queues():
    for mode in MODES:
        refresh_queue(mode)


# ======================================================================
# Pencere
# ======================================================================
gui = QtBind.init(__name__, pName)

MODE_TAB_BOX = {'fate': (10, 52), 'fortune': (62, 68), 'pen': (130, 73)}
PAGE_TAB_BOX = {'setup': (330, 62), 'queue': (392, 70), 'history': (462, 70), 'settings': (532, 75)}

# Ust serit
QtBind.createLabel(gui, panel_html(704, 30, INK), 4, 2)
QtBind.createLabel(gui, '<font color="%s" size="4"><b>✦ %s</b></font>' % (GOLD, pName), 14, 6)
_credit = 'Ver: %s &nbsp;&nbsp; Geliştirici: %s' % (pVersion, html_safe(pDeveloper))
if pBaseCredit:
    _credit += ' &nbsp;&nbsp; Temel: %s' % html_safe(pBaseCredit)
QtBind.createLabel(gui, '<font color="%s">%s</font>' % (DARK_MUTED, _credit), 440, 10)

# Gezinme
QtBind.createButton(gui, 'show_fate', 'Fate', 10, 38)
QtBind.createButton(gui, 'show_fortune', 'Fortune', 62, 38)
QtBind.createButton(gui, 'show_pen', 'Pen', 130, 38)
QtBind.createButton(gui, 'page_setup', 'Eşya', 330, 38)
QtBind.createButton(gui, 'page_queue', 'Kuyruk', 392, 38)
QtBind.createButton(gui, 'page_history', 'Geçmiş', 462, 38)
QtBind.createButton(gui, 'page_settings', 'Ayarlar', 532, 38)
mode_bar = QtBind.createLabel(gui, '', 10, 64)
page_bar = QtBind.createLabel(gui, '', 330, 64)

# Durum cubugu
QtBind.createLabel(gui, panel_html(704, 22, INK), 4, 282)
lbl_status = QtBind.createLabel(gui, fixed_width_text(
    '<font color="%s"><b>Hazır</b></font>' % LEVEL_DARK['muted'], 690), 12, 286)

setup_widgets = {mode: [] for mode in MODES}
queue_widgets = {mode: [] for mode in MODES}
history_widgets = []
settings_widgets = []
inventory_lists = {}
selected_labels = {}
stat_lists = {}
target_lists = {}
target_inputs = {}
match_logic_widgets = {}
queue_lists = {}
result_labels = {}
dashboard_labels = {}
delay_edits = {}


def title_html(text, color=PAPER_TEXT):
    return '<font color="%s"><b>%s</b></font>' % (color, text)


def muted_html(text):
    return '<font color="%s">%s</font>' % (PAPER_MUTED, text)


def place(group, widget, x, y):
    group.append((widget, x, y))
    return widget


# --- Esya sayfasi (her mod icin) ---
for _mode in MODES:
    _group = setup_widgets[_mode]
    _accent = ACCENT[_mode]
    place(_group, QtBind.createLabel(gui, panel_html(372, 204, PAPER, _accent), OFFSCREEN_X, 72), 4, 72)
    place(_group, QtBind.createLabel(gui, panel_html(326, 204, PAPER, _accent), OFFSCREEN_X, 72), 382, 72)
    place(_group, QtBind.createLabel(
        gui, title_html('ENVANTER · %s' % MODE_LABELS[_mode].upper()), OFFSCREEN_X, 78), 14, 78)
    place(_group, QtBind.createButton(gui, _mode + '_refresh_inventory', '↻ Yenile', OFFSCREEN_X, 94), 14, 94)
    place(_group, QtBind.createButton(gui, _mode + '_inspect', 'Seç', OFFSCREEN_X, 94), 96, 94)
    place(_group, QtBind.createButton(gui, _mode + '_test', 'Tek Roll', OFFSCREEN_X, 94), 150, 94)
    inventory_lists[_mode] = place(_group, QtBind.createList(gui, OFFSCREEN_X, 120, 352, 104), 14, 120)
    selected_labels[_mode] = place(_group, QtBind.createLabel(gui, fixed_width_text(
        muted_html('Henüz eşya seçilmedi'), 350), OFFSCREEN_X, 230), 14, 230)
    if _mode == 'fate':
        place(_group, QtBind.createLabel(gui, title_html('HEDEF MAVİ SATIR'), OFFSCREEN_X, 78), 392, 78)
        target_inputs[_mode] = place(_group, QtBind.createLineEdit(gui, '6', OFFSCREEN_X, 104, 48, 20), 392, 104)
        place(_group, QtBind.createButton(gui, 'fate_queue_item', 'Kuyruğa Ekle', OFFSCREEN_X, 100), 452, 100)
        place(_group, QtBind.createLabel(gui, muted_html(
            'Seçili eşyaya Wheel of Fate atar.<br>'
            'Mavi satır sayısı hedefe ulaşınca durur.<br><br>'
            'İlk roll eşyanın mevcut mavilerini<br>değiştirir; kıymetli eşyada dikkat.'),
            OFFSCREEN_X, 140), 392, 140)
    else:
        place(_group, QtBind.createLabel(gui, title_html('STATLAR'), OFFSCREEN_X, 78), 392, 78)
        place(_group, QtBind.createLabel(gui, title_html('HEDEFLER'), OFFSCREEN_X, 78), 550, 78)
        stat_lists[_mode] = place(_group, QtBind.createList(gui, OFFSCREEN_X, 98, 150, 88), 392, 98)
        target_lists[_mode] = place(_group, QtBind.createList(gui, OFFSCREEN_X, 98, 150, 88), 550, 98)
        target_inputs[_mode] = place(_group, QtBind.createLineEdit(
            gui, '1' if _mode == 'fortune' else '10', OFFSCREEN_X, 192, 50, 20), 392, 192)
        place(_group, QtBind.createButton(gui, _mode + '_add_target', 'Ekle / Güncelle', OFFSCREEN_X, 188), 450, 188)
        place(_group, QtBind.createButton(gui, _mode + '_remove_target', 'Hedefi Sil', OFFSCREEN_X, 188), 550, 188)
        if _mode == 'fortune':
            _combo = QtBind.createCombobox(gui, OFFSCREEN_X, 222, 130, 20)
            QtBind.append(gui, _combo, 'Hepsi (VE)')
            QtBind.append(gui, _combo, 'Herhangi (VEYA)')
            match_logic_widgets[_mode] = place(_group, _combo, 392, 222)
            place(_group, QtBind.createButton(gui, 'fortune_queue_item', 'Kuyruğa Ekle', OFFSCREEN_X, 218), 535, 218)
        else:
            place(_group, QtBind.createButton(gui, 'pen_queue_item', 'Kuyruğa Ekle', OFFSCREEN_X, 218), 392, 218)

# --- Kuyruk sayfasi (her mod icin) ---
for _mode in MODES:
    _group = queue_widgets[_mode]
    _accent = ACCENT[_mode]
    place(_group, QtBind.createLabel(gui, panel_html(480, 204, PAPER, _accent), OFFSCREEN_X, 72), 4, 72)
    place(_group, QtBind.createLabel(
        gui, title_html('OTOMASYON KUYRUĞU · %s' % MODE_LABELS[_mode].upper()), OFFSCREEN_X, 78), 14, 78)
    queue_lists[_mode] = place(_group, QtBind.createList(gui, OFFSCREEN_X, 98, 462, 70), 14, 98)
    place(_group, QtBind.createButton(gui, _mode + '_remove_queue', 'Kaldır', OFFSCREEN_X, 174), 14, 174)
    place(_group, QtBind.createButton(gui, _mode + '_clear_queue', 'Temizle', OFFSCREEN_X, 174), 80, 174)
    place(_group, QtBind.createButton(gui, _mode + '_start', '▶ BAŞLAT', OFFSCREEN_X, 206), 14, 206)
    place(_group, QtBind.createButton(gui, 'stop_clicked', '■ DURDUR', OFFSCREEN_X, 206), 100, 206)
    place(_group, QtBind.createLabel(gui, '<font color="%s"><b>⚠ Roll mevcut mavileri değiştirir</b></font>' %
                                     LEVEL_LIGHT['err'], OFFSCREEN_X, 212), 200, 212)
    result_labels[_mode] = place(_group, QtBind.createLabel(gui, fixed_width_text(
        muted_html('Henüz doğrulanmış sonuç yok'), 450), OFFSCREEN_X, 244), 14, 244)
    dashboard_labels[_mode] = place(_group, QtBind.createLabel(gui, '', OFFSCREEN_X, 72), 490, 72)

# --- Gecmis sayfasi ---
place(history_widgets, QtBind.createLabel(gui, panel_html(704, 204, PAPER, GOLD), OFFSCREEN_X, 72), 4, 72)
place(history_widgets, QtBind.createLabel(gui, title_html('ROLL GEÇMİŞİ (son 200)'), OFFSCREEN_X, 78), 14, 78)
lst_history = place(history_widgets, QtBind.createList(gui, OFFSCREEN_X, 98, 684, 122), 14, 98)
place(history_widgets, QtBind.createButton(gui, 'history_open_clicked', 'Dosyayı Aç', OFFSCREEN_X, 230), 14, 230)
place(history_widgets, QtBind.createButton(gui, 'history_clear_clicked', 'Listeyi Temizle', OFFSCREEN_X, 230), 100, 230)
place(history_widgets, QtBind.createLabel(gui, muted_html(
    'Kayıtlar Log/RWheelManager/RWheelManager_history.txt dosyasına da yazılır'), OFFSCREEN_X, 236), 230, 236)

# --- Ayarlar sayfasi ---
place(settings_widgets, QtBind.createLabel(gui, panel_html(704, 204, PAPER, GOLD), OFFSCREEN_X, 72), 4, 72)
place(settings_widgets, QtBind.createLabel(gui, title_html('BEKLEMELER (ms)'), OFFSCREEN_X, 78), 14, 78)
for _row, (_text, _key) in enumerate((('Fate', 'fate'), ('Fortune', 'fortune'), ('Pen', 'pen'))):
    place(settings_widgets, QtBind.createLabel(gui, muted_html(_text), OFFSCREEN_X, 104 + _row * 26), 14, 104 + _row * 26)
    delay_edits[_key] = place(settings_widgets, QtBind.createLineEdit(
        gui, str(settings['delay_' + _key]), OFFSCREEN_X, 100 + _row * 26, 60, 20), 150, 100 + _row * 26)
place(settings_widgets, QtBind.createLabel(gui, muted_html('Sonraki eşya'), OFFSCREEN_X, 182), 14, 182)
edit_next = place(settings_widgets, QtBind.createLineEdit(
    gui, str(settings['next_item']), OFFSCREEN_X, 178, 60, 20), 150, 178)
place(settings_widgets, QtBind.createLabel(gui, muted_html('Cevap zaman aşımı (sn)'), OFFSCREEN_X, 208), 14, 208)
edit_timeout = place(settings_widgets, QtBind.createLineEdit(
    gui, str(settings['timeout']), OFFSCREEN_X, 204, 60, 20), 150, 204)
place(settings_widgets, QtBind.createLabel(gui, title_html('DAVRANIŞ'), OFFSCREEN_X, 78), 250, 78)
chk_jitter = place(settings_widgets, QtBind.createCheckBox(
    gui, 'jitter_changed', 'Beklemelere rastgele sapma ekle', OFFSCREEN_X, 100), 250, 100)
chk_confirm = place(settings_widgets, QtBind.createCheckBox(
    gui, 'confirm_changed', 'Başlatmadan önce onay iste', OFFSCREEN_X, 124), 250, 124)
chk_precheck = place(settings_widgets, QtBind.createCheckBox(
    gui, 'precheck_changed', 'Hedefte olan eşyayı atla (ön kontrol)', OFFSCREEN_X, 148), 250, 148)
chk_debug = place(settings_widgets, QtBind.createCheckBox(
    gui, 'debug_changed', 'Debug to TXT', OFFSCREEN_X, 172), 250, 172)
place(settings_widgets, QtBind.createButton(gui, 'settings_apply_clicked', 'Uygula ve Kaydet', OFFSCREEN_X, 200), 250, 200)
place(settings_widgets, QtBind.createButton(gui, 'settings_load_clicked', 'Dosyadan Yükle', OFFSCREEN_X, 200), 360, 200)
place(settings_widgets, QtBind.createButton(gui, 'debug_folder_clicked', 'Debug Klasörü', OFFSCREEN_X, 228), 250, 228)
place(settings_widgets, QtBind.createLabel(gui, title_html('SCRIPT KOMUTU'), OFFSCREEN_X, 78), 500, 78)
place(settings_widgets, QtBind.createLabel(gui, muted_html(
    'RWheel,fate<br>RWheel,fortune<br>RWheel,pen<br>RWheel,stop<br><br>'
    'Kayıtlı kuyruğu başlatır ve<br>hemen döner; bitişi için<br>script\'e wait ekle.<br>'
    '(Canlıda doğrulanmadı)'), OFFSCREEN_X, 102), 500, 102)

show_view('fate', 'setup')
sync_settings_widgets()
try:
    load_state()
except Exception as _error:
    plugin_log('Ayarlar yüklenemedi: %s' % _error)
refresh_history_list()

log('[%s] Loaded' % pName)
