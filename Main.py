from pyrogram import Client
from pyrogram.raw.functions.channels import JoinChannel, LeaveChannel, ReportSpam as ChannelReportSpam
from pyrogram.raw.functions.messages import Report, ReportSpam
from pyrogram.raw.functions.account import ReportPeer
from pyrogram.raw.types import (
    InputPeerChannel, 
    InputPeerUser,
    InputPeerChat,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonSpam,
    InputReportReasonCopyright,
    InputReportReasonGeoIrrelevant,
    InputReportReasonFake,
    InputReportReasonIllegalDrugs,
    InputReportReasonPersonalDetails,
    InputReportReasonOther
)
import re
import time
import os
import json
import random
import threading
import logging
import sys
import configparser
import platform
import datetime
import signal
import asyncio
import queue
import traceback

# Setup logging
os.makedirs("logs", exist_ok=True)
log_file = f"logs/telegram_reporter_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Detect platform
IS_ANDROID = 'android' in platform.system().lower() or os.path.exists('/data/data/com.termux')
IS_WINDOWS = platform.system().lower() == 'windows'

# Global variables
report_results = queue.Queue()
active_threads = 0
thread_lock = threading.Lock()

# ====================== ADVANCED CONFIGURATION ======================

# 7 Proxy IPs for rotation (change every 4-5 reports)
PROXY_IPS = [
    "5.101.109.1", "85.214.132.117", "91.14.133.7",
    "62.53.2.123", "62.53.11.237", "99.86.7.22", "46.87.7.5"
]

# Real User Profiles (EU Citizens for DSA reports)
USER_PROFILES = [
    {"country": "Germany", "name": "Ortrud Wernecke", "address": "Barthweg 7, 14209 Vechta", "email": "ortrud.wernecke@gmail.com", "phone": "+49 709 444 625"},
    {"country": "Germany", "name": "Heinz Gumprich", "address": "Abraham-Döring-Ring 96, 44672 Rosenheim", "email": "heinz.gumprich@gmail.com", "phone": "+49 359 763 974"},
    {"country": "France", "name": "Helene Delahaye", "address": "23, avenue Riou, 91793 Royer-la-Forêt", "email": "helene.delahaye@gmail.com", "phone": "+33 575 435 410"},
    {"country": "France", "name": "Theodore Pierre", "address": "28, chemin de Becker, 04974 Sainte Zoé", "email": "theodore.pierre@gmail.com", "phone": "+33 693 677 947"},
    {"country": "Poland", "name": "Blanka Kusztal", "address": "ulica Wyszyńskiego 302, 09-498 Tychy", "email": "blanka.kusztal@gmail.com", "phone": "+48 968 459 700"},
    {"country": "Poland", "name": "Ksawery Kieca", "address": "plac Hallera 66/45, 52-564 Zgorzelec", "email": "ksawery.kieca@gmail.com", "phone": "+48 405 023 419"},
    {"country": "Spain", "name": "Leoncio Portillo", "address": "Alameda de Lorenza Hoyos 776 Piso 3 , Valladolid, 34535", "email": "leoncio.portillo@gmail.com", "phone": "+34 460 697 313"},
    {"country": "Spain", "name": "Encarnita Garces", "address": "Camino de Mirta Mayo 76, Santa Cruz de Tenerife, 21121", "email": "encarnita.garces@gmail.com", "phone": "+34 810 161 584"},
    {"country": "Netherlands", "name": "Yassin Willemsen", "address": "Ayasteeg 711, 6161 XB, Dalerveen", "email": "yassin.willemsen@gmail.com", "phone": "+31 542 970 740"},
    {"country": "Netherlands", "name": "Silke Smit", "address": "Mikering 542, 4127QB, Hapert", "email": "silke.smit@gmail.com", "phone": "+31 296 857 854"}
]

# 8 DSA Messages
DSA_MESSAGES = [
    "This channel is unlawfully distributing paid educational content that is protected by copyright. The content is being shared without permission from the rights holder. Please investigate and take appropriate action.",
    "This channel appears to be sharing premium course materials without authorization. Such distribution violates copyright laws and Telegram's Terms of Service. Kindly review this channel.",
    "The channel is engaged in unauthorized sharing of copyrighted educational resources, including paid courses. Please verify the infringement and take necessary enforcement action.",
    "This channel is providing access to premium learning content that is normally available only through paid subscriptions. The content is being redistributed without permission from the copyright owner.",
    "I would like to report this channel for copyright infringement. It is distributing protected course content without authorization and potentially causing harm to the content owner.",
    "This channel is repeatedly uploading and sharing copyrighted premium educational materials. Please review the reported content and take action if it violates Telegram policies.",
    "The reported channel appears to be operating as a piracy source for paid educational courses. The content is being shared without the consent of the copyright holder.",
    "This channel is distributing copyrighted premium courses and study materials without authorization. I request that Telegram investigate this matter and take appropriate action if violations are confirmed."
]

# 5 Strict Messages
STRICT_MESSAGES = [
    "This channel is repeatedly distributing copyrighted content without authorization and appears to be in clear violation of applicable copyright laws and Telegram’s own policies. Failure to take appropriate action against such blatant infringement raises serious concerns regarding compliance and enforcement. Immediate review and removal of this channel is strongly warranted.",
    "This channel is facilitating large-scale copyright infringement through the unauthorized distribution of protected content. Its continued operation undermines the rights of content owners and reflects a serious breach of Telegram’s platform rules. Urgent enforcement action is necessary.",
    "The infringement occurring through this channel is neither isolated nor accidental. It demonstrates a persistent pattern of unauthorized content distribution that directly violates copyright protections. Prompt removal is required to maintain legal and policy compliance.",
    "This channel is openly engaged in the dissemination of copyrighted material without permission from the respective rights holders. Allowing such activity to continue raises significant compliance concerns and warrants immediate corrective action.",
    "The content shared by this channel constitutes a clear and ongoing violation of copyright law. Continued availability of this channel enables further infringement and weakens the effectiveness of platform enforcement measures. Immediate review and removal are justified."
]

# Fixed EU Law Header
REPORT_HEADLINE = "I am reporting illegal content under the Union law"
EU_COPYRIGHT_URL = "https://digital-strategy.ec.europa.eu/en/policies/copyright"

# ====================== FUNCTIONS ======================

def display_banner():
    colors_supported = not IS_WINDOWS or os.environ.get('ANSICON') is not None
    if colors_supported:
        banner = """
\033[91m████████╗███████╗██╗     ███████╗ ██████╗ ██████╗  █████╗ ███╗   ███╗
\033[91m╚══██╔══╝██╔════╝██║     ██╔════╝██╔════╝ ██╔══██╗██╔══██╗████╗ ████║
\033[93m   ██║   █████╗  ██║     █████╗  ██║  ███╗██████╔╝███████║██╔████╔██║
\033[93m   ██║   ██╔══╝  ██║     ██╔══╝  ██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║
\033[92m   ██║   ███████╗███████╗███████╗╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
\033[92m   ╚═╝   ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
\033[96m██████╗ ███████╗██████╗  ██████╗ ██████╗ ████████╗███████╗██████╗ 
\033[96m██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗
\033[94m██████╔╝█████╗  ██████╔╝██║   ██║██████╔╝   ██║   █████╗  ██████╔╝
\033[94m██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██╔══██╗   ██║   ██╔══╝  ██╔══██╗
\033[95m██║  ██║███████╗██║     ╚██████╔╝██║  ██║   ██║   ███████╗██║  ██║
\033[95m╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
\033[0m
\033[96m[+]\033[0m Advanced DSA Telegram Mass Reporter v4.1 (Mustfa Edition)
\033[96m[+]\033[0m IP Rotation + Real EU Users + Union Law Header
\033[96m[+]\033[0m Platform: {0}
""".format("Android/Termux" if IS_ANDROID else "Windows" if IS_WINDOWS else "Linux/Mac")
    else:
        banner = "[+] Advanced DSA Telegram Mass Reporter v4.1\n"
    print(banner)

def load_config():
    config = configparser.ConfigParser()
    config_file = "config.ini"
    if not os.path.exists(config_file):
        config['DEFAULT'] = {
            'api_id': '33853339',
            'api_hash': 'd44e3a158d9da849df318173268f94c0',
            'session_prefix': 'report_session',
            'use_proxy': 'True',
            'proxy_type': 'socks5',
            'proxy_addr': '127.0.0.1',
            'proxy_port': '1080',
            'proxy_username': '',
            'proxy_password': '',
            'delay_between_reports': '2',
            'retry_attempts': '3',
            'auto_leave': 'True',
            'random_delay': 'True',
            'min_delay': '2.0',
            'max_delay': '5.0',
            'memory_optimization': 'True',
            'session_retry_count': '3',
            'session_retry_delay': '5'
        }
        with open(config_file, 'w') as f:
            config.write(f)
        logging.info(f"Created default configuration file: {config_file}")
    config.read(config_file)
    return config['DEFAULT']

def get_report_reason(reason_code):
    return ("Copyright", InputReportReasonCopyright())

def get_random_dsa_message():
    return random.choice(DSA_MESSAGES)

def get_random_strict_message():
    return random.choice(STRICT_MESSAGES)

def get_random_user_profile():
    return random.choice(USER_PROFILES)

def build_advanced_report_message(entity_name):
    parts = [
        REPORT_HEADLINE,
        f"Reference: {EU_COPYRIGHT_URL}",
        get_random_dsa_message(),
        get_random_strict_message()
    ]
    if random.random() < 0.70:
        profile = get_random_user_profile()
        parts.append(f"Complainant: {profile['name']} ({profile['country']})")
        parts.append(f"Address: {profile['address']}")
        parts.append(f"Email: {profile['email']} | Phone: {profile['phone']}")
    return "\n\n".join(parts)

def setup_proxy(client, config, ip_index=0):
    if config.getboolean('use_proxy'):
        proxy_ip = PROXY_IPS[ip_index % len(PROXY_IPS)]
        proxy = {
            "scheme": config.get('proxy_type', 'socks5'),
            "hostname": proxy_ip,
            "port": config.getint('proxy_port', 1080)
        }
        client.proxy = proxy
        logging.info(f"Using Proxy IP → {proxy_ip}")
        print(f"\033[96m[+]\033[0m Proxy IP: {proxy_ip}")
    else:
        logging.info("Using real user IP")

def report_channel_post(app, peer, message_id, reason_obj, reason_name, entity_name):
    message = build_advanced_report_message(entity_name)
    return app.invoke(Report(peer=peer, id=[message_id], reason=reason_obj, message=message))

def report_entity(app, peer, reason_obj, reason_name, entity_name):
    message = build_advanced_report_message(entity_name)
    return app.invoke(ReportPeer(peer=peer, reason=reason_obj, message=message))

def report_channel_spam(app, peer):
    return app.invoke(ChannelReportSpam(channel=peer, participant=[], id=[]))

def report_spam(app, peer):
    return app.invoke(ReportSpam(peer=peer))

def setup_asyncio_for_thread():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
    except Exception as e:
        logging.error(f"Failed to set up asyncio loop: {e}")
        return None

def cleanup_asyncio_loop(loop):
    try:
        if loop and loop.is_running():
            loop.stop()
        if loop and not loop.is_closed():
            loop.close()
    except Exception as e:
        logging.error(f"Error cleaning up asyncio loop: {e}")

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        print()

def get_random_delay(config):
    if config.getboolean('random_delay'):
        return random.uniform(config.getfloat('min_delay'), config.getfloat('max_delay'))
    return config.getfloat('delay_between_reports')

def report_with_account(session_name, config, entity_type, entity_id, message_id, reason_code, total_reports):
    global active_threads
    with thread_lock:
        active_threads += 1
    
    loop = setup_asyncio_for_thread()
    if not loop:
        with thread_lock:
            active_threads -= 1
        report_results.put({'session': session_name, 'success': False, 'error': "Async loop failed", 'reports_sent': 0})
        return

    success_count = 0
    error_message = None
    ip_index = random.randint(0, len(PROXY_IPS)-1)

    try:
        app = Client(session_name, config.get('api_id'), config.get('api_hash'))
        setup_proxy(app, config, ip_index)
        
        with app:
            try:
                if entity_type == "channel_post" or entity_type == "entity":
                    if isinstance(entity_id, int):
                        peer = app.resolve_peer(entity_id)
                    else:
                        peer = app.resolve_peer(entity_id)
                    
                    if hasattr(peer, 'channel_id'):
                        input_peer = InputPeerChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
                        entity_name = f"@{entity_id}" if isinstance(entity_id, str) else f"Channel {entity_id}"
                    elif hasattr(peer, 'user_id'):
                        input_peer = InputPeerUser(user_id=peer.user_id, access_hash=peer.access_hash)
                        entity_name = f"@{entity_id}" if isinstance(entity_id, str) else f"User {entity_id}"
                    elif hasattr(peer, 'chat_id'):
                        input_peer = InputPeerChat(chat_id=peer.chat_id)
                        entity_name = f"Chat {peer.chat_id}"
                    else:
                        raise ValueError(f"Unknown peer type: {type(peer)}")
                
                elif entity_type == "user":
                    peer = app.resolve_peer(entity_id)
                    input_peer = InputPeerUser(user_id=peer.user_id, access_hash=peer.access_hash)
                    entity_name = f"User {entity_id}"
                
                elif entity_type == "private":
                    try:
                        chat = app.join_chat(f"https://t.me/+{entity_id}")
                        peer = app.resolve_peer(chat.id)
                        if hasattr(peer, 'channel_id'):
                            input_peer = InputPeerChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)
                        elif hasattr(peer, 'chat_id'):
                            input_peer = InputPeerChat(chat_id=peer.chat_id)
                        entity_name = f"Private chat {chat.title}"
                    except Exception as e:
                        logging.error(f"Failed to join private chat: {e}")
                        raise
                else:
                    logging.error(f"Unknown entity type: {entity_type}")
                    raise ValueError(f"Unknown entity type: {entity_type}")
            except Exception as e:
                logging.error(f"Failed to resolve peer with session {session_name}: {e}")
                print(f"\033[91m[!]\033[0m [{session_name}] Failed to resolve peer: {e}")
                raise

            if entity_type == "channel_post" and hasattr(peer, 'channel_id') and config.getboolean('auto_leave', True):
                try:
                    app.invoke(JoinChannel(channel=peer))
                    logging.info(f"[{session_name}] Joined {entity_name}")
                    print(f"\033[96m[+]\033[0m [{session_name}] Joined {entity_name}")
                    time.sleep(random.uniform(1.0, 3.0))
                except Exception as e:
                    logging.error(f"[{session_name}] Join failed: {e}")
                    print(f"\033[91m[!]\033[0m [{session_name}] Join failed: {e}")

            reason_name, reason_obj = get_report_reason(reason_code)
            retry_attempts = config.getint('retry_attempts')
            
            print(f"\033[96m[+]\033[0m [{session_name}] Starting Advanced DSA Reports for {entity_name}...")

            for i in range(total_reports):
                if i > 0 and i % 5 == 0:
                    ip_index = (ip_index + 1) % len(PROXY_IPS)
                    logging.info(f"[{session_name}] Rotating Proxy IP at report {i+1}")

                for attempt in range(retry_attempts):
                    try:
                        if entity_type == "channel_post":
                            report_channel_post(app, input_peer, message_id, reason_obj, reason_name, entity_name)
                            if random.random() < 0.3:
                                try:
                                    report_channel_spam(app, peer)
                                except Exception:
                                    pass
                        else:
                            report_entity(app, input_peer, reason_obj, reason_name, entity_name)
                            if random.random() < 0.5:
                                try:
                                    if hasattr(peer, 'channel_id'):
                                        report_channel_spam(app, peer)
                                    else:
                                        report_spam(app, input_peer)
                                except Exception:
                                    pass
                        
                        success_count += 1
                        print_progress_bar(i + 1, total_reports, prefix=f'[{session_name}]', suffix=f'({i+1}/{total_reports})')
                        time.sleep(get_random_delay(config))
                        break
                    except Exception as e:
                        if attempt < retry_attempts - 1:
                            time.sleep(get_random_delay(config) * 2)
                        else:
                            logging.error(f"[{session_name}] Failed report {i + 1}: {e}")
                            print(f"\033[91m[!]\033[0m [{session_name}] Failed report {i + 1}: {e}")
                            break

            print(f"\033[92m[+]\033[0m [{session_name}] Successfully sent {success_count}/{total_reports} reports")
            logging.info(f"[{session_name}] Successfully sent {success_count}/{total_reports} reports")

            if (entity_type == "channel_post" or entity_type == "private") and hasattr(peer, 'channel_id') and config.getboolean('auto_leave', True):
                try:
                    app.invoke(LeaveChannel(channel=peer))
                    logging.info(f"[{session_name}] Left {entity_name}")
                    print(f"\033[96m[+]\033[0m [{session_name}] Left {entity_name}")
                except Exception as e:
                    logging.error(f"[{session_name}] Failed to leave: {e}")
                    print(f"\033[91m[!]\033[0m [{session_name}] Failed to leave: {e}")

    except Exception as e:
        error_message = str(e)
        logging.error(f"Error in session {session_name}: {e}")
        logging.error(traceback.format_exc())
        print(f"\033[91m[!]\033[0m Error in session {session_name}: {e}")
    
    finally:
        cleanup_asyncio_loop(loop)
        with thread_lock:
            active_threads -= 1
        report_results.put({
            'session': session_name,
            'success': success_count > 0,
            'error': error_message,
            'reports_sent': success_count
        })

# ====================== HELPER FUNCTIONS (ORIGINAL + ENHANCED) ======================
def check_sessions(session_prefix, num_accounts):
    existing_sessions = []
    for i in range(1, num_accounts + 1):
        session_name = f"{session_prefix}_{i}"
        if os.path.exists(f"{session_name}.session"):
            existing_sessions.append(session_name)
    return existing_sessions

def create_session(session_name, config):
    loop = setup_asyncio_for_thread()
    if not loop:
        print(f"\033[91m[!]\033[0m Failed to set up asyncio loop for session creation")
        return False
    try:
        api_id = config.get('api_id')
        api_hash = config.get('api_hash')
        print(f"\033[96m[+]\033[0m Creating new session: {session_name}")
        print(f"\033[93m[!]\033[0m You'll need to log in with a phone number.")
        app = Client(session_name, api_id, api_hash)
        setup_proxy(app, config, random.randint(0, len(PROXY_IPS)-1))
        with app:
            me = app.get_me()
            print(f"\033[92m[+]\033[0m Successfully created session for {me.first_name}")
            return True
    except Exception as e:
        logging.error(f"Failed to create session {session_name}: {e}")
        print(f"\033[91m[!]\033[0m Failed to create session {session_name}: {e}")
        return False
    finally:
        cleanup_asyncio_loop(loop)

def signal_handler(sig, frame):
    print(f"\n\033[91m[!]\033[0m Operation cancelled by user")
    sys.exit(0)

def extract_entity_info(link):
    channel_post_match = re.search(r"https?://t\.me/([^/]+)/(\d+)", link)
    if channel_post_match:
        return "channel_post", channel_post_match.group(1), int(channel_post_match.group(2))
    channel_match = re.search(r"https?://t\.me/([^/]+)$", link)
    if channel_match:
        return "entity", channel_match.group(1), None
    private_match = re.search(r"https?://t\.me/\+([a-zA-Z0-9_-]+)$", link)
    if private_match:
        return "private", private_match.group(1), None
    user_id_match = re.search(r"tg://user\?id=(\d+)", link)
    if user_id_match:
        return "user", int(user_id_match.group(1)), None
    logging.error("Invalid Telegram link format")
    return None, None, None

def save_target_list(targets, filename="targets.json"):
    try:
        with open(filename, 'w') as f:
            json.dump(targets, f, indent=4)
        print(f"\033[92m[+]\033[0m Target list saved to {filename}")
    except Exception as e:
        logging.error(f"Failed to save target list: {e}")
        print(f"\033[91m[!]\033[0m Failed to save target list: {e}")

def load_target_list(filename="targets.json"):
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                targets = json.load(f)
            print(f"\033[92m[+]\033[0m Loaded {len(targets)} targets from {filename}")
            return targets
        else:
            print(f"\033[93m[!]\033[0m Target list file not found: {filename}")
            return []
    except Exception as e:
        logging.error(f"Failed to load target list: {e}")
        print(f"\033[91m[!]\033[0m Failed to load target list: {e}")
        return []

def main():
    signal.signal(signal.SIGINT, signal_handler)
    display_banner()
    config = load_config()
    
    if IS_ANDROID:
        print(f"\033[93m[!]\033[0m Running on Android/Termux. Optimizing for mobile environment...")
        if config.getboolean('memory_optimization', True):
            print(f"\033[96m[+]\033[0m Memory optimization enabled for mobile devices")
    
    print(f"\033[96m[+]\033[0m Select target type:")
    print(f"\033[96m[1]\033[0m Channel/Group Post")
    print(f"\033[96m[2]\033[0m Channel/Group/Bot")
    print(f"\033[96m[3]\033[0m User")
    print(f"\033[96m[4]\033[0m Private Chat")
    print(f"\033[96m[5]\033[0m Load targets from file")
    
    target_type = int(input("\033[96m[?]\033[0m Select target type (1-5): "))
    targets = []
    
    if target_type == 5:
        targets = load_target_list()
        if not targets:
            print(f"\033[91m[!]\033[0m No targets loaded. Exiting.")
            return
    else:
        if target_type == 1:
            link = input("\033[96m[?]\033[0m Channel post link (https://t.me/channel/123): ")
            entity_type, entity_id, message_id = extract_entity_info(link)
        elif target_type == 2:
            link = input("\033[96m[?]\033[0m Channel/Group/Bot link (https://t.me/username): ")
            entity_type, entity_id, message_id = extract_entity_info(link)
        elif target_type == 3:
            user_input = input("\033[96m[?]\033[0m User ID or username: ")
            if user_input.isdigit():
                entity_type, entity_id, message_id = "user", int(user_input), None
            else:
                entity_type, entity_id, message_id = "entity", user_input.lstrip('@'), None
        elif target_type == 4:
            link = input("\033[96m[?]\033[0m Private chat invite link (https://t.me/+abc123): ")
            entity_type, entity_id, message_id = extract_entity_info(link)
        else:
            print(f"\033[91m[!]\033[0m Invalid option")
            return
        
        if entity_type is None:
            print(f"\033[91m[!]\033[0m Failed to parse the provided link or ID")
            return
        
        print("\n\033[93m[!]\033[0m Available report reasons:")
        print("\033[96m[1]\033[0m Violence")
        print("\033[96m[2]\033[0m Pornography")
        print("\033[96m[3]\033[0m Spam")
        print("\033[96m[4]\033[0m Copyright")
        print("\033[96m[5]\033[0m Geo Irrelevant")
        print("\033[96m[6]\033[0m Fake")
        print("\033[96m[7]\033[0m Illegal Drugs")
        print("\033[96m[8]\033[0m Personal Details")
        print("\033[96m[9]\033[0m Other")
        
        reason_code = int(input("\n\033[96m[?]\033[0m Select report reason (1-9): "))
        
        targets.append({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'message_id': message_id,
            'reason_code': reason_code
        })
        
        save_target = input("\033[96m[?]\033[0m Save this target for future use? (y/n): ").lower() == 'y'
        if save_target:
            save_target_list(targets)
    
    num_accounts = int(input("\033[96m[?]\033[0m Number of accounts to use: "))
    reports_per_account = int(input("\033[96m[?]\033[0m Reports per account: "))
    
    session_prefix = config.get('session_prefix')
    existing_sessions = check_sessions(session_prefix, num_accounts)
    
    if len(existing_sessions) < num_accounts:
        print(f"\033[93m[!]\033[0m Found {len(existing_sessions)} existing sessions, need {num_accounts}")
        create_new = input("\033[96m[?]\033[0m Create missing sessions? (y/n): ").lower() == 'y'
        if create_new:
            for i in range(1, num_accounts + 1):
                session_name = f"{session_prefix}_{i}"
                if session_name not in existing_sessions:
                    if create_session(session_name, config):
                        existing_sessions.append(session_name)
        else:
            num_accounts = len(existing_sessions)
            if num_accounts == 0:
                print(f"\033[91m[!]\033[0m No sessions available. Exiting.")
                return
    
    for target_idx, target in enumerate(targets):
        print(f"\n\033[96m[+]\033[0m Processing target {target_idx + 1}/{len(targets)}")
        entity_type = target['entity_type']
        entity_id = target['entity_id']
        message_id = target['message_id']
        reason_code = target['reason_code']
        
        threads = []
        for i in range(1, num_accounts + 1):
            session_name = f"{session_prefix}_{i}"
            if os.path.exists(f"{session_name}.session"):
                thread = threading.Thread(
                    target=report_with_account,
                    args=(session_name, config, entity_type, entity_id, message_id, reason_code, reports_per_account)
                )
                threads.append(thread)
                thread.start()
                time.sleep(0.5)
        
        while active_threads > 0:
            time.sleep(0.5)
        
        total_reports = 0
        failed_sessions = []
        while not report_results.empty():
            result = report_results.get()
            total_reports += result['reports_sent']
            if not result['success']:
                failed_sessions.append((result['session'], result['error']))
        
        print(f"\n\033[92m[+]\033[0m Target {target_idx + 1} reporting completed!")
        print(f"\033[96m[i]\033[0m Total reports sent: {total_reports}")
        
        if failed_sessions:
            print(f"\033[93m[!]\033[0m {len(failed_sessions)} sessions failed:")
            for session, error in failed_sessions:
                print(f"\033[91m[-]\033[0m {session}: {error}")
            
            retry_count = config.getint('session_retry_count')
            if retry_count > 0:
                retry = input(f"\033[96m[?]\033[0m Retry failed sessions? (y/n): ").lower() == 'y'
                if retry:
                    for retry_attempt in range(retry_count):
                        if not failed_sessions:
                            break
                        print(f"\033[96m[+]\033[0m Retry attempt {retry_attempt + 1}/{retry_count}")
                        retry_delay = config.getint('session_retry_delay')
                        time.sleep(retry_delay)
                        current_failed = failed_sessions.copy()
                        failed_sessions = []
                        retry_threads = []
                        for session, _ in current_failed:
                            thread = threading.Thread(target=report_with_account, args=(session, config, entity_type, entity_id, message_id, reason_code, reports_per_account))
                            retry_threads.append(thread)
                            thread.start()
                            time.sleep(0.5)
                        while active_threads > 0:
                            time.sleep(0.5)
                        retry_reports = 0
                        while not report_results.empty():
                            result = report_results.get()
                            retry_reports += result['reports_sent']
                            if not result['success']:
                                failed_sessions.append((result['session'], result['error']))
                        total_reports += retry_reports
                        print(f"\033[96m[i]\033[0m Retry sent {retry_reports} additional reports")
                        if not failed_sessions:
                            print(f"\033[92m[+]\033[0m All retries successful!")
                            break
    
    print(f"\n\033[92m[+]\033[0m All reporting tasks completed!")
    print(f"\033[96m[i]\033[0m Check the log file for detailed information: {log_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\033[91m[!]\033[0m Operation cancelled by user")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.error(traceback.format_exc())
        print(f"\n\033[91m[!]\033[0m An error occurred: {e}")
        print(f"\033[96m[i]\033[0m Check the log file for details: {log_file}")
