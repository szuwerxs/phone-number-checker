import time
import requests
import phonenumbers
from phonenumbers import geocoder, carrier, timezone, PhoneNumberFormat
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich import box

VOIP_PREFIXES = ["4470", "4484", "4487", "4857", "4858"]
DISPOSABLE_PREFIXES = ["4475", "4478", "4879"]
PREMIUM_PREFIXES = ["900", "901", "902", "905", "976"]
CORPORATE_PREFIXES = ["700", "800", "801", "804"]
CALLCENTER_HINTS = ["callcenter", "telemarket", "contact-center"]

SUSPICIOUS_CARRIERS = ["GlobalTel", "Call4Free", "VoipPlanet", "SapoTel", "EuroGlobal"]
SPAM_SOURCES = ["nieznany-numer.pl", "sync.me", "tellows.com", "tnie.pl"]
SPAM_KEYWORDS = ["scam"]

PROGRESS_DELAY = 0.3
RISK_THRESHOLD = 70
SPAM_TIMEOUT = 4

NUMBER_TYPE_NAMES = {
    0: "Unknown", 1: "Fixed line", 2: "Mobile", 3: "VoIP",
    4: "Toll-free", 5: "Premium", 6: "Shared-cost", 7: "Personal number",
    8: "Pager", 9: "UAN", 10: "Voicemail", 11: "Short code", 12: "Standard rate"
}

SUSPICIOUS_FLAGS = [
    "[blue]VoIP[/blue] suspicion", "[yellow]Disposable[/yellow] suspicion", "[magenta]Premium-rate[/magenta] suspicion",
    "[cyan]Corporate[/cyan] line suspicion", "[green]Call-center[/green] guess", "[red]Suspicious[/red] carrier?",
    "[orange1]Bot-like[/orange1] pattern?", "[bold red]Reported as spam/scam[/bold red]?"
]

console = Console()

def has_suspicious_prefix(number: str, prefixes: list) -> bool:
    return any(number.startswith(p) for p in prefixes)


def has_bot_pattern(number: str) -> bool:
    sorted_asc = "".join(sorted(number))
    sorted_desc = "".join(sorted(number, reverse=True))
    unique_digits = len(set(number))
    return number == sorted_asc or number == sorted_desc or unique_digits <= 2


def check_spam_databases(number: str, progress=None, task=None):
    found_reports = []
    for site in SPAM_SOURCES:
        try:
            url = f"https://{site}/search/{number}"
            html = requests.get(url, timeout=SPAM_TIMEOUT).text.lower()
            if any(keyword in html for keyword in SPAM_KEYWORDS):
                found_reports.append(site)
        except Exception:
            pass
        if progress and task:
            progress.update(task, advance=1)
    
    is_reported = len(found_reports) > 0
    details = f"Found reports on: {', '.join(found_reports)}" if is_reported else "No spam records found"
    return is_reported, details


def generate_risk_score(info: dict) -> int:
    score = 0
    if info.get("[blue]VoIP[/blue] suspicion"):
        score += 20
    if info.get("[yellow]Disposable[/yellow] suspicion"):
        score += 25
    if info.get("[magenta]Premium-rate[/magenta] suspicion"):
        score += 15
    if info.get("[bold red]Reported[/bold red] as spam/scam?"):
        score += 30
    if info.get("[red]Suspicious[/red] carrier?"):
        score += 10
    if info.get("[orange1]Bot-like[/orange1] pattern?"):
        score += 10
    return min(score, 100)


def hlr_lookup(api, number):
    return {"status": "HLR disabled in demo"}


def analyze_with_progress(phone_number: str):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=True,
    ) as progress:

        task1 = progress.add_task("[cyan]Parsing number...", total=1)
        task2 = progress.add_task("[cyan]Checking carrier...", total=1)
        task3 = progress.add_task("[cyan]Scanning spam databases...", total=len(SPAM_SOURCES))
        task4 = progress.add_task("[cyan]Calculating risk score...", total=1)

        try:
            parsed = phonenumbers.parse(phone_number)
        except Exception:
            progress.stop()
            error_panel = Panel("[red]Invalid phone number format[/red]", title="Error", border_style="red")
            console.print(error_panel)
            return None

        progress.update(task1, advance=1)
        time.sleep(PROGRESS_DELAY)

        info = {}
        info["[cyan]Phone[/cyan] number"] = phone_number
        info["[blue]Country[/blue]"] = geocoder.description_for_number(parsed, "en") or "Unknown"
        info["[green]Carrier[/green]"] = carrier.name_for_number(parsed, "en") or "Unknown"
        info["[yellow]Timezone[/yellow]"] = ", ".join(timezone.time_zones_for_number(parsed))

        formatted_e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
        info["[magenta]E.164[/magenta] format"] = formatted_e164
        info["[magenta]International[/magenta] format"] = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
        info["[magenta]National[/magenta] format"] = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)

        info["[blue]Region[/blue] code"] = parsed.country_code
        info["[blue]Prefix[/blue]"] = f"+{parsed.country_code}"
        info["[blue]National[/blue] number"] = parsed.national_number
        info["[green]Possible[/green] number?"] = phonenumbers.is_possible_number(parsed)
        info["[green]Valid[/green] number?"] = phonenumbers.is_valid_number(parsed)

        number_type = phonenumbers.number_type(parsed)
        info["[cyan]Number[/cyan] type"] = NUMBER_TYPE_NAMES.get(number_type, "Other")

        phone_digits = formatted_e164.replace("+", "")
        info["[blue]VoIP[/blue] suspicion"] = has_suspicious_prefix(phone_digits, VOIP_PREFIXES)
        info["[yellow]Disposable[/yellow] suspicion"] = has_suspicious_prefix(phone_digits, DISPOSABLE_PREFIXES)
        info["[magenta]Premium-rate[/magenta] suspicion"] = has_suspicious_prefix(phone_digits, PREMIUM_PREFIXES)
        info["[cyan]Corporate[/cyan] line suspicion"] = has_suspicious_prefix(phone_digits, CORPORATE_PREFIXES)

        carrier_name = info["[green]Carrier[/green]"].lower()
        info["[green]Call-center[/green] guess"] = any(hint in carrier_name for hint in CALLCENTER_HINTS)
        info["[red]Suspicious[/red] carrier?"] = info["[green]Carrier[/green]"] in SUSPICIOUS_CARRIERS
        info["[orange1]Bot-like[/orange1] pattern?"] = has_bot_pattern(phone_digits)
        info["[blue]Length[/blue] OK for region?"] = phonenumbers.is_possible_number(parsed)

        progress.update(task2, advance=1)
        time.sleep(PROGRESS_DELAY)

        is_spam_reported, spam_details = check_spam_databases(phone_digits, progress, task3)
        info["[bold red]Reported[/bold red] as spam/scam?"] = is_spam_reported
        info["[magenta]Scam[/magenta] report details"] = spam_details

        progress.update(task3, completed=len(SPAM_SOURCES))
        time.sleep(PROGRESS_DELAY)

        info["[bold yellow]Risk[/bold yellow] score (0-100)"] = generate_risk_score(info)
        info["[cyan]HLR[/cyan]/[cyan]MNP[/cyan]"] = "Not enabled (demo)"
        info["[blue]Reverse[/blue] search"] = "Not implemented (legal restrictions)"

        progress.update(task4, advance=1)
        time.sleep(PROGRESS_DELAY)

        return info


def display_results(info: dict):
    table = Table(title="Phone OSINT Report", box=box.ROUNDED, title_style="bold cyan")
    table.add_column("Field", style="cyan", no_wrap=False)
    table.add_column("Value", style="white")

    for key, value in info.items():
        if isinstance(value, bool):
            if key in SUSPICIOUS_FLAGS:
                display_value = "[red]Yes[/red]" if value else "[green]No[/green]"
            else:
                display_value = "[green]Yes[/green]" if value else "[red]No[/red]"
        else:
            display_value = str(value)
        table.add_row(key, display_value)

    console.print(table)

    score = info["[bold yellow]Risk[/bold yellow] score (0-100)"]
    if score < 30:
        color = "green"
        level = "Low"
    elif score < 60:
        color = "yellow"
        level = "Medium"
    else:
        color = "red"
        level = "High"

    risk_text = (
        f"[bold {color}]Risk Score: {score}/100 ({level})[/bold {color}] "
        f"— Ignore until it gets above {RISK_THRESHOLD}\n\n"
    )
    risk_text += "Contributing factors:\n"

    factors = []
    if info["[blue]VoIP[/blue] suspicion"]:
        factors.append("• VoIP suspicion")
    if info["[yellow]Disposable[/yellow] suspicion"]:
        factors.append("• Disposable number suspicion")
    if info["[magenta]Premium-rate[/magenta] suspicion"]:
        factors.append("• Premium-rate suspicion")
    if info["[bold red]Reported[/bold red] as spam/scam?"]:
        factors.append("• Reported as spam/scam")
    if info["[red]Suspicious[/red] carrier?"]:
        factors.append("• Suspicious carrier")
    if info["[orange1]Bot-like[/orange1] pattern?"]:
        factors.append("• Bot-like pattern")

    if not factors:
        factors.append("• No significant risk factors detected")

    risk_text += "\n".join(factors)

    risk_panel = Panel(risk_text, title="Risk Analysis", border_style=color, title_align="left")
    console.print(risk_panel)


def main():
    banner = """
╔══════════════════════════════════════╗
║     Phone number info v2 beta        ║
║      made by @szuwer                 ║
╚══════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")

    phone = console.input(
        Panel(
            "[bold yellow]Enter phone number (with country code, e.g. +48123456789):[/bold yellow]",
            title="Input",
            border_style="blue",
        )
    ).strip()

    if not phone:
        console.print("[red]No number provided. Exiting.[/red]")
        return

    info = analyze_with_progress(phone)
    if info is None:
        return

    display_results(info)

    console.print("\n[bold]Press Enter to exit...[/bold]", end="")
    input()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user. Goodbye![/yellow]")
