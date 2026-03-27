import threading
import requests
import time
import phonenumbers
from datetime import datetime
from phonenumbers import geocoder, carrier, timezone, PhoneNumberFormat
import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("Dark")

VOIP_PREFIXES = ["4470", "4484", "4487", "4857", "4858"]
burners = ["4475", "4478", "4879"]
PREMIUM = ["900", "901", "902", "905", "976"]
P_CORP = ["700", "800", "801", "804"]
C_HINT = ["callcenter", "telemarket", "contact-center"]

badCarriers = {"GlobalTel", "Call4Free", "VoipPlanet", "SapoTel", "EuroGlobal"}
spam_urls = ["sync.me", "tellows.com", "tnie.pl"]

thms = {
    "v": {"t1": "#C77DFF", "t2": "#7B2CBF", "ac": "#F72585", "b1": "#7209B7", "b2": "#4361EE", "bg0": "#080010", "bg1": "#120024", "bd": "#3C096C"},
    "b": {"t1": "#90E0EF", "t2": "#0077B6", "ac": "#00B4D8", "b1": "#023E8A", "b2": "#0096C7", "bg0": "#000814", "bg1": "#001D3D", "bd": "#003566"},
    "g": {"t1": "#B7E4C7", "t2": "#40916C", "ac": "#52B788", "b1": "#2D6A4F", "b2": "#74C69D", "bg0": "#081C15", "bg1": "#1B4332", "bd": "#2D6A4F"}
}

def h2r(h): return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
def r2h(r,g,b): return f'#{int(r):02x}{int(g):02x}{int(b):02x}'
def mix_c(c1, c2, f):
    a,b,c = h2r(c1)
    x,y,z = h2r(c2)
    return r2h(a+(x-a)*f, b+(y-b)*f, c+(z-c)*f)

def GlowBtn(mstr, txt, cmd, thm="v", **k):
    c = thms[thm]
    b = ctk.CTkButton(mstr, text=txt, command=cmd, fg_color=c["b1"], hover_color=c["b2"],
        border_color=c["bd"], border_width=2, corner_radius=10, font=ctk.CTkFont(size=18, weight="bold"), **k)
    b.f = 0.0
    b.tid = None
    b.ac = c["ac"]
    b.bd = c["bd"]
    
    def anim(tg):
        if b.tid: b.after_cancel(b.tid)
        d = tg - b.f
        if abs(d) < 0.1:
            b.f = tg
            if tg > 0.5: b.configure(border_color=b.ac, border_width=3)
            else: b.configure(border_color=b.bd, border_width=2)
            return
        b.f += 0.1 if d>0 else -0.1
        b.configure(border_color=mix_c(b.bd, b.ac, b.f))
        b.tid = b.after(16, anim, tg)

    b.bind("<Enter>", lambda e: anim(1.0) if b.cget("state")=="normal" else None)
    b.bind("<Leave>", lambda e: anim(0.0))
    return b

def waCheck(num):
    try:
        r = requests.get(f"https://api.whatsapp.com/send/?phone={num}", timeout=3, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://google.com"
        })
        if "Looks like you don't have WhatsApp installed" in r.text or "Share on WhatsApp" in r.text:
            return True, "Registered"
        return False, "Not registered"
    except:
        return False, "Failed"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Phone number info puller")
        
        self.update_idletasks()
        w, h = 1125, 625
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth() - w) // 2}+{(self.winfo_screenheight() - h) // 2}")
        self.minsize(900, 500)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.cur_t = "v"
        c = thms["v"]
        self.configure(fg_color=c["bg0"])
        
        self.head = ctk.CTkFrame(self, fg_color="transparent")
        self.head.grid(row=0, column=0, padx=20, pady=(30, 10), sticky="ew")
        
        self.l_tit = ctk.CTkLabel(self.head, text="Phone Number info puller", font=ctk.CTkFont(size=32, weight="bold"), text_color=c["t1"])
        self.l_tit.pack(side="left")
        
        dbg = ctk.CTkFrame(self.head, fg_color="transparent")
        dbg.pack(side="right", anchor="e")
        self.lbl_t = ctk.CTkLabel(dbg, text="Time: --", font=("Courier", 13), text_color=c["t2"])
        self.lbl_t.pack(anchor="e")
        self.lbl_size = ctk.CTkLabel(dbg, text=f"Size: {w}x{h}", font=("Courier", 13), text_color=c["t2"])
        self.lbl_size.pack(anchor="e")
        self.bind("<Configure>", lambda e: self.lbl_size.configure(text=f"Size: {self.winfo_width()}x{self.winfo_height()}") if e.widget == self else None)

        cf = ctk.CTkFrame(dbg, fg_color="transparent")
        cf.pack(anchor="e", pady=2)
        ctk.CTkButton(cf, width=12, height=12, fg_color="#74C69D", corner_radius=6, text="", command=lambda: self.sw("g")).pack(side="right", padx=2)
        ctk.CTkButton(cf, width=12, height=12, fg_color="#00B4D8", corner_radius=6, text="", command=lambda: self.sw("b")).pack(side="right", padx=2)
        ctk.CTkButton(cf, width=12, height=12, fg_color="#F72585", corner_radius=6, text="", command=lambda: self.sw("v")).pack(side="right", padx=2)

        self.inp_frm = ctk.CTkFrame(self, corner_radius=15, border_width=1, fg_color=c["bg1"], border_color=c["bd"])
        self.inp_frm.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.inp_frm.grid_columnconfigure(0, weight=1)
        
        self.entry = ctk.CTkEntry(self.inp_frm, placeholder_text="Enter phone number (+48...)", font=ctk.CTkFont(size=18), height=50, border_width=2, border_color=c["bd"], fg_color=c["bg0"], text_color=c["t1"], corner_radius=10)
        self.entry.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")
        self.entry.bind("<Return>", lambda e: self.analyze_click())
        
        self.btn = GlowBtn(self.inp_frm, txt="ANALYZE", cmd=self.analyze_click, thm=self.cur_t)
        self.btn.grid(row=0, column=1, padx=(10, 20), pady=20)
        
        self.res_frm = ctk.CTkScrollableFrame(self, label_text="Analysis Results", label_font=ctk.CTkFont(size=18, weight="bold"), corner_radius=15, border_width=1, fg_color=c["bg1"], border_color=c["bd"], label_text_color=c["t1"])
        self.res_frm.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.res_frm.grid_columnconfigure(0, weight=1)
        self.res_frm.grid_columnconfigure(1, weight=3)
        
        ftr = ctk.CTkFrame(self, fg_color="transparent")
        ftr.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        ftr.grid_columnconfigure(0, weight=1)
        
        self.status = ctk.CTkLabel(ftr, text="Ready...", width=250, anchor="w", font=ctk.CTkFont(size=15, slant="italic"), text_color=c["t2"])
        self.status.grid(row=0, column=0, padx=0, pady=(0, 6), sticky="w")
        
        self.prog = ctk.CTkProgressBar(ftr, height=8, progress_color=c["ac"], fg_color=c["bd"])
        self.prog.grid(row=1, column=0, sticky="ew")
        self.prog.set(0)

        self.ovr = ctk.CTkFrame(self, fg_color=c["bg0"])
        self.ovr.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.l_intro = ctk.CTkLabel(self.ovr, text="Made with ❤️ by @szuwer", font=ctk.CTkFont(size=38, weight="bold"), text_color=c["ac"])
        self.l_intro.place(relx=0.5, rely=0.5, anchor="center")
        
        self.o_f = 1.0
        def f_ovr():
            self.o_f -= 0.05
            if self.o_f <= 0:
                self.ovr.destroy()
                return
            self.l_intro.configure(text_color=mix_c(thms[self.cur_t]["bg0"], thms[self.cur_t]["ac"], self.o_f))
            self.after(30, f_ovr)
        self.after(1500, f_ovr)

        self.tick()

    def sw(self, t):
        self.cur_t = t
        c = thms[t]
        self.configure(fg_color=c["bg0"])
        self.l_tit.configure(text_color=c["t1"])
        self.lbl_t.configure(text_color=c["t2"])
        self.lbl_size.configure(text_color=c["t2"])
        self.inp_frm.configure(fg_color=c["bg1"], border_color=c["bd"])
        self.entry.configure(fg_color=c["bg0"], border_color=c["bd"], text_color=c["t1"])
        
        self.btn.configure(fg_color=c["b1"], hover_color=c["b2"], border_color=c["bd"])
        self.btn.ac = c["ac"]
        self.btn.bd = c["bd"]
        self.res_frm.configure(fg_color=c["bg1"], border_color=c["bd"], label_text_color=c["t1"], scrollbar_button_color=c["b1"], scrollbar_button_hover_color=c["b2"])
        self.status.configure(text_color=c["t2"])
        self.prog.configure(fg_color=c["bd"], progress_color=c["ac"])
        
        for w in self.res_frm.winfo_children():
            if isinstance(w, ctk.CTkLabel):
                if w.cget("text") in ["Analysis Results", "Notes:"]: w.configure(text_color=c["t1"])
                elif "Risk" not in w.cget("text") and w.cget("text_color") not in ["#FF1F5A", "#52B788", "#FFCA3A"]: w.configure(text_color=c["t1"])
            elif isinstance(w, ctk.CTkFrame):
                w.configure(fg_color=c["b1"])

    def tick(self):
        self.lbl_t.configure(text=f"Time: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
        self.after(1000, self.tick)
        
    def anim_pb(self, tg, cur=None):
        if cur is None: cur = self.prog.get()
        if hasattr(self, "pb_id") and self.pb_id: self.after_cancel(self.pb_id)
        d = tg - cur
        if abs(d) < 0.02:
            self.prog.set(tg)
            return
        cur += d * 0.2
        self.prog.set(cur)
        self.pb_id = self.after(16, self.anim_pb, tg, cur)

    def append_row(self, r, k, v, danger=False):
        c = thms[self.cur_t]
        clr = c["t1"]
        if isinstance(v, bool):
            vs = "Yes" if v else "No"
            if k == "WhatsApp": 
                clr = "#52B788" if v else "#FF1F5A"
            else:
                clr = "#FF1F5A" if (v and danger) or (not v and not danger) else "#52B788"
                if not danger and v: clr = "#52B788" 
        else:
            vs = str(v)
            
        ctk.CTkLabel(self.res_frm, text=k, font=ctk.CTkFont(weight="bold", size=15), text_color=c["t2"]).grid(row=r, column=0, padx=15, pady=8, sticky="w")
        ctk.CTkLabel(self.res_frm, text=vs, text_color=clr, font=ctk.CTkFont(size=15)).grid(row=r, column=1, padx=5, pady=8, sticky="w")

    def analyze_click(self):
        p = self.entry.get().strip()
        if not p:
            return messagebox.showwarning("ERR", "Number empty")
        if p == "1234":
            messagebox.showerror("No", "seriously?")
            return
            
        for child in self.res_frm.winfo_children():
            child.destroy()
            
        self.btn.configure(state="disabled")
        self.prog.set(0)
        self.status.configure(text="Init...")
        
        threading.Thread(target=self.do_scan, args=(p,), daemon=True).start()

    def do_scan(self, phoneStr):
        tot = 4 + len(spam_urls)
        step = 0
        
        try:
            if phoneStr.startswith("+") and "+" in phoneStr[1:]:
                raise ValueError("Too many pluses")
                
            parsed = phonenumbers.parse(phoneStr)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid format")
        except Exception as e:
            self.after(0, lambda: [self.status.configure(text=str(e)[:40]), self.btn.configure(state="normal"), self.anim_pb(0.0)])
            return
            
        step+=1
        self.after(0, lambda: [self.anim_pb(step/tot), self.status.configure(text="Fetching geo...")])
        
        digits = phonenumbers.format_number(parsed, PhoneNumberFormat.E164).replace("+", "")
        carrierName = carrier.name_for_number(parsed, "en") or "Unknown"
        
        tz_list = []
        try:
            for tz in timezone.time_zones_for_number(parsed):
                if "/" in tz: tz_list.append(tz.split("/")[1].replace("_", " "))
                else: tz_list.append(tz)
            tz_str = " | ".join(tz_list)
        except: tz_str = "Unknown"

        voip_match = any(digits.startswith(x) for x in VOIP_PREFIXES)
        disp_match = any(digits.startswith(x) for x in burners)
        prem_match = any(digits.startswith(x) for x in PREMIUM)
        corp_match = any(digits.startswith(x) for x in P_CORP)
        cc_guess = any(x in carrierName.lower() for x in C_HINT)
        bad_car = carrierName in badCarriers
        
        is_bot = (digits == "".join(sorted(digits))) or (len(set(digits)) <= 2)
        nType = {0: "?", 1: "Fixed", 2: "Mobile", 3: "VoIP"}.get(phonenumbers.number_type(parsed), "Other")

        results = {
            "Country": f"+{parsed.country_code}",
            "Area": geocoder.description_for_number(parsed, "en") or "Unknown",
            "Timezone": tz_str,
            "Carrier": carrierName,
            "Type": nType,
            "VoIP?": voip_match,
            "Disposable?": disp_match,
            "Premium?": prem_match,
            "Corporate?": corp_match,
            "Call Center?": cc_guess,
            "Bad Carrier?": bad_car,
            "Bot structure?": is_bot
        }
        
        step+=1
        self.after(0, lambda: [self.anim_pb(step/tot), self.status.configure(text="WA Check...")])
        has_wa, _ = waCheck(digits)
        results["WhatsApp"] = has_wa
        
        step+=1
        self.after(0, lambda: [self.anim_pb(step/tot), self.status.configure(text="Spam DBs...")])
        
        spam_hits = []
        for url in spam_urls:
            try:
                t_out = 5 if url == "sync.me" else 3
                req = requests.get(f"https://{url}/search/{digits}", timeout=t_out).text.lower()
                if "scam" in req or "spam" in req or "fraud" in req:
                    spam_hits.append(url)
            except: pass
            step+=1
            self.after(0, lambda s=step: self.anim_pb(s/tot))
            
        results["Spam recorded?"] = len(spam_hits) > 0
        results["DBs"] = ", ".join(spam_hits) if spam_hits else "None"
        
        self.after(0, lambda: self.status.configure(text="Scoring..."))
        time.sleep(0.1) 
        
        s = 0
        if voip_match: s += 20
        if disp_match: s += 25
        if prem_match: s += 15
        if len(spam_hits) > 0: s += 30
        if bad_car: s += 10
        if is_bot: s+=10
        
        if voip_match and is_bot: s = 100
        if not has_wa and nType == "Mobile": s += 5
        if s > 100: s = 100
        
        self.after(0, self.render_final, results, s)

    def render_final(self, data, score):
        self.status.configure(text="Finished", text_color="#52B788")
        self.anim_pb(1.0)
        self.btn.configure(state="normal")
        
        r_idx = 0
        for k, v in data.items():
            self.append_row(r_idx, k, v, danger=k.endswith("?"))
            r_idx += 1
            
        c_th = thms[self.cur_t]
        ctk.CTkFrame(self.res_frm, height=2, fg_color=c_th["b1"]).grid(row=r_idx, column=0, columnspan=2, sticky="ew", pady=15, padx=15)
        r_idx += 1
        
        c = "#FF1F5A" if score >= 60 else "#FFCA3A" if score >= 30 else "#52B788"
        l = "High" if score >= 60 else "Medium" if score >= 30 else "Low"
            
        ctk.CTkLabel(self.res_frm, text=f"Risk: {score}/100 ({l})", font=ctk.CTkFont(size=26, weight="bold"), text_color=c).grid(row=r_idx, column=0, columnspan=2, sticky="w", padx=15, pady=5)
        r_idx+=1
        
        ctk.CTkLabel(self.res_frm, text="— Ignore until it gets above 70%", font=ctk.CTkFont(size=14, slant="italic"), text_color=c_th["t2"]).grid(row=r_idx, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 15))
        r_idx+=1
        
        f = []
        if data["VoIP?"]: f.append("VOIP prefix")
        if data["Disposable?"]: f.append("Burner prefix")
        if data["Corporate?"]: f.append("Corporate prefix matched")
        if data["Call Center?"]: f.append("Carrier strings imply Call Center")
        if data["Spam recorded?"]: f.append("Found in spam DBs")
        if score == 100 and data["VoIP?"] and data["Bot structure?"]: f.append("Critical: VOIP Bot detected")
        if data["WhatsApp"] is False and data["Type"] == "Mobile": f.append("Missing WhatsApp (weird for mobile)")
        
        if len(f) == 0: f = ["Clean"]
            
        ctk.CTkLabel(self.res_frm, text="Notes:\n- " + "\n- ".join(f), font=ctk.CTkFont(size=16), justify="left", text_color=c_th["t1"]).grid(row=r_idx, column=0, columnspan=2, sticky="w", padx=15)

if __name__ == "__main__":
    App().mainloop()
