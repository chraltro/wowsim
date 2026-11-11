#!/usr/bin/env python3
"""Run the ClaudeExport addon outside the game and write the export it produces.

    python3 test/addon_run.py            # writes test/sample_export.txt
    python3 test/addon_run.py --check    # fails if the addon no longer produces that file

The addon cannot be tested in the game from here, so this loads ClaudeExport.lua in a
real Lua 5.1 with a stand-in for the Classic-style part of the WoW API, and plays a
made-up level 14 Dwarf Shaman in Loch Modan: open bank, open the Leatherworking window,
scan the auction house, export. It catches syntax errors and broken sections, and it is
where test/sample_export.txt (the input of test/check.js) comes from.

It does not prove the calls exist on the Forever client. Only the game can.

Needs lupa:  pip install lupa
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "test", "sample_export.txt")

try:
    from lupa import lua51
except ImportError:
    sys.exit("lupa is not installed (pip install lupa)")

ITEMS = {str(i["id"]): i for i in json.load(open(os.path.join(ROOT, "data", "items_all.json")))["items"]}
CRAFT_ITEMS = json.load(open(os.path.join(ROOT, "data", "crafts.json")))["I"]

EQUIP_LOC = {"Chest": "INVTYPE_CHEST", "Legs": "INVTYPE_LEGS", "Feet": "INVTYPE_FEET", "Back": "INVTYPE_CLOAK",
             "Hands": "INVTYPE_HAND", "Head": "INVTYPE_HEAD", "Shoulder": "INVTYPE_SHOULDER", "Waist": "INVTYPE_WAIST",
             "Wrist": "INVTYPE_WRIST", "Finger": "INVTYPE_FINGER", "Neck": "INVTYPE_NECK", "Trinket": "INVTYPE_TRINKET",
             "Two-Hand": "INVTYPE_2HWEAPON", "One-Hand": "INVTYPE_WEAPON", "Main Hand": "INVTYPE_WEAPONMAINHAND",
             "Off Hand": "INVTYPE_WEAPONOFFHAND", "Shield": "INVTYPE_SHIELD", "Held In Off-hand": "INVTYPE_HOLDABLE"}
LOC_TEXT = {"INVTYPE_CHEST": "Chest", "INVTYPE_LEGS": "Legs", "INVTYPE_FEET": "Feet", "INVTYPE_CLOAK": "Back",
            "INVTYPE_HAND": "Hands", "INVTYPE_HEAD": "Head", "INVTYPE_SHOULDER": "Shoulder", "INVTYPE_WAIST": "Waist",
            "INVTYPE_WRIST": "Wrist", "INVTYPE_FINGER": "Finger", "INVTYPE_NECK": "Neck", "INVTYPE_TRINKET": "Trinket",
            "INVTYPE_2HWEAPON": "Two-Hand", "INVTYPE_WEAPON": "One-Hand", "INVTYPE_WEAPONMAINHAND": "Main Hand",
            "INVTYPE_WEAPONOFFHAND": "Off Hand", "INVTYPE_SHIELD": "Off Hand", "INVTYPE_HOLDABLE": "Held In Off-hand"}
STAT_TEXT = [("str", "Strength"), ("agi", "Agility"), ("sta", "Stamina"), ("int", "Intellect"), ("spi", "Spirit")]
QUALITY = {0: "Poor", 1: "Common", 2: "Uncommon", 3: "Rare", 4: "Epic"}


def item_record(iid):
    """What GetItemInfo and the tooltip say about an item, built from the repo's own data."""
    it = ITEMS.get(str(iid))
    if not it:
        c = CRAFT_ITEMS.get(str(iid))
        name = c[0] if c else {6948: "Hearthstone"}.get(iid, "Item %d" % iid)
        return {"name": name, "quality": c[1] if c else 1, "ilvl": c[8] if c else 1, "req": 0, "subclass": "",
                "loc": "", "sell": c[2] if c else 0, "classID": 7, "lines": []}
    loc = EQUIP_LOC.get(it["slot"], "")
    sub = it.get("armorType") or it.get("weaponType") or ""
    lines = ["Binds when equipped"]
    w = it.get("weapon")
    if w:
        lines.append("%s  %s" % (it["slot"], sub))
        lines.append("%d - %d Damage  Speed %.2f" % (w["min"], w["max"], w["speed"]))
        lines.append("(%.1f damage per second)" % ((w["min"] + w["max"]) / 2 / w["speed"]))
    else:
        lines.append("%s  %s" % (it["slot"], sub) if sub else it["slot"])
    s = it.get("stats") or {}
    if s.get("armor"): lines.append("%d Armor" % s["armor"])
    for k, label in STAT_TEXT:
        if s.get(k): lines.append("+%d %s" % (s[k], label))
    if s.get("healing"):
        lines.append("Equip: Increases healing done by spells and effects by up to %d." % s["healing"])
    if s.get("spellDamage") and not s.get("healing"):
        lines.append("Equip: Increases damage and healing done by magical spells and effects by up to %d." % s["spellDamage"])
    if s.get("mp5"): lines.append("Equip: Restores %d mana per 5 sec." % s["mp5"])
    if (it.get("reqLvl") or 0) > 1: lines.append("Requires Level %d" % it["reqLvl"])
    sell = (CRAFT_ITEMS.get(str(iid)) or [0, 0, 0])[2]
    return {"name": it["name"], "quality": it["quality"], "ilvl": it["ilvl"], "req": it.get("reqLvl") or 0,
            "subclass": sub, "loc": loc, "sell": sell, "classID": 2 if w else 4, "lines": lines}


# The made-up character -------------------------------------------------------------------------------------------
EQUIPPED = {5: 2961, 7: 10549, 8: 2569, 15: 2580, 16: 3103}                    # inventory slot -> item
BAGS = [(6948, 1), (1959, 1), (2312, 1), (2318, 14), (783, 2), (2320, 5), (4540, 4), (159, 8)]
BANK = [(2318, 20), (2589, 37)]
QUESTS = [  # header, title, level, id, complete, objectives, goal, xp, choices
    ("Loch Modan", "Filthy Paws", 15, 307, False, [("Miners' Gear: 2/4", False)],
     "Bring 4 crates of Miners' Gear to Mountaineer Stormpike.", 1050, [3160, 3161, 3166]),
    ("Loch Modan", "In Defense of the King's Lands", 12, 224, True, [("Stonesplinter Trogg slain: 10/10", True),
     ("Stonesplinter Scout slain: 10/10", True)], "Kill 10 Stonesplinter Troggs and 10 Stonesplinter Scouts.", 910, []),
    ("Loch Modan", "Thelsamar Blood Sausages", 11, 418, False, [("Boar Intestines: 1/3", False), ("Bear Meat: 3/3", True),
     ("Spider Ichor: 0/3", False)], "Bring 3 Boar Intestines, 3 Bear Meat and 3 Spider Ichor to Vidra Hearthstove.", 840, []),
]
COMPLETED = [179, 233, 234, 170, 3106, 183, 282, 420, 218, 2160, 400, 5541, 317, 318, 319, 320, 313, 412, 310, 311,
             287, 291, 315, 413, 414, 432, 433, 419, 417, 314, 94373, 94374, 94375, 96243, 416, 6387, 6391, 6388, 6392, 267]
TALENTS = [("Elemental Combat", []), ("Enhancement", []), ("Restoration", [("Tidal Focus", 5, 5, 1)])]
SKILLS = [("Class Skills", None), ("Restoration", (70, 70)), ("Enhancement", (70, 70)), ("Elemental Combat", (70, 70)),
          ("Professions", None), ("Leatherworking", (62, 75)), ("Skinning", (74, 75)),
          ("Secondary Skills", None), ("First Aid", (40, 75)), ("Cooking", (35, 75)),
          ("Weapon Skills", None), ("Maces", (68, 70)), ("Two-Handed Maces", (41, 70)), ("Unarmed", (12, 70))]
RECIPES = [("Handstitched Leather Boots", "trivial"), ("Light Armor Kit", "trivial"), ("Handstitched Leather Vest", "trivial"),
           ("Light Leather", "trivial"), ("Handstitched Leather Belt", "easy"), ("Handstitched Leather Cloak", "easy"),
           ("Cured Light Hide", "easy"), ("Embossed Leather Vest", "medium"), ("Embossed Leather Gloves", "medium"),
           ("Embossed Leather Cloak", "optimal")]
# Auction listings: (item, stack, buyout for the stack). Gear a Shaman can wear at 14, plus a few materials.
AUCTIONS = [(1959, 1, 1300), (1959, 1, 1500), (1405, 1, 4900), (1473, 1, 2300), (2823, 1, 2900), (3195, 1, 1400),
            (1945, 1, 400), (2312, 1, 800), (2988, 1, 500), (2974, 1, 500), (3205, 1, 500), (2984, 1, 300),
            (2582, 1, 700), (2969, 1, 500), (2973, 1, 800), (2987, 1, 500), (1929, 1, 3200), (1933, 1, 9000),
            (2318, 20, 600), (2318, 20, 640), (783, 5, 575), (2320, 0, 0), (4231, 2, 900), (2319, 10, 2450)]

LUA_API = r'''
local D = MOCK
local function link(id) return "|cff1eff00|Hitem:" .. id .. ":0:0:0|h[" .. D.items[id].name .. "]|h|r" end
local frames, handlers = {}, {}
local function newFrame(kind, name)
  local f = { shown = true }
  local mt = { __index = function(t, k)
    if k == "SetScript" then return function(self, ev, fn) if ev == "OnEvent" then handlers[#handlers + 1] = fn end end end
    if k == "IsShown" then return function(self) return self.shown end end
    if k == "Show" then return function(self) self.shown = true end end
    if k == "Hide" then return function(self) self.shown = false end end
    if k == "CreateFontString" or k == "CreateTexture" then return function() return newFrame("Region") end end
    if k == "SetText" then return function(self, s) self.text = s end end
    if k == "GetText" then return function(self) return self.text end end
    if k == "SetHyperlink" then return function(self, l)
        local id = tonumber(l:match("item:(%d+)")); self.lines = { D.items[id].name }
        for _, x in ipairs(D.items[id].lines) do self.lines[#self.lines + 1] = x end
        for i, x in ipairs(self.lines) do
          local left, right = x:match("^(.-)  (.+)$")
          _G[name .. "TextLeft" .. i] = { GetText = function() return left or x end }
          _G[name .. "TextRight" .. i] = { GetText = function() return right end, IsShown = function() return right ~= nil end }
        end
        return true
      end end
    if k == "NumLines" then return function(self) return self.lines and #self.lines or 0 end end
    return function() end
  end }
  setmetatable(f, mt)
  if name then _G[name] = f end
  return f
end
function CreateFrame(kind, name) return newFrame(kind, name) end
function FireEvent(e) for _, fn in ipairs(handlers) do fn(nil, e) end end
UIParent, WorldFrame, UISpecialFrames, SlashCmdList, ChatFontNormal = {}, {}, {}, {}, {}
tinsert = table.insert
date = function(f) return D.now end
print = function(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring(select(i, ...)) end; D.printed[#D.printed + 1] = table.concat(t, " ") end
C_Timer = { After = function(_, fn) fn() end }
function InCombatLockdown() return false end
function ReloadUI() D.reloaded = true end
for q, n in pairs({ [0] = "Poor", "Common", "Uncommon", "Rare", "Epic" }) do _G["ITEM_QUALITY" .. q .. "_DESC"] = n end
for k, v in pairs(D.locText) do _G[k] = v end
for i, n in ipairs({ "Strength", "Agility", "Stamina", "Intellect", "Spirit" }) do _G["SPELL_STAT" .. i .. "_NAME"] = n end
for i, n in ipairs({ "Hated", "Hostile", "Unfriendly", "Neutral", "Friendly", "Honored", "Revered", "Exalted" }) do _G["FACTION_STANDING_LABEL" .. i] = n end
NUM_BAG_SLOTS, NUM_BANKBAGSLOTS, BANK_CONTAINER, BOOKTYPE_SPELL = 4, 6, -1, "spell"

function UnitName() return "Thrainor" end
function GetRealmName() return "Forever" end
function UnitRace() return "Dwarf" end
function UnitClass() return "Shaman" end
function UnitLevel() return 14 end
function UnitFactionGroup() return "Alliance" end
function GetGuildInfo() return nil end
function UnitXP() return 5120 end
function UnitXPMax() return 12300 end
function GetXPExhaustion() return 3400 end
function GetMoney() return 31250 end
function GetZoneText() return "Loch Modan" end
function GetSubZoneText() return "Thelsamar" end
function GetBindLocation() return "Thelsamar" end
function UnitCharacterPoints() return 0 end
function UnitStat(_, i) local v = ({ 33, 21, 40, 38, 41 })[i]; return v, v end
function UnitHealthMax() return 472 end
function UnitPowerMax() return 610 end
function UnitArmor() return 0, 342 end
function UnitAttackPower() return 84, 0, 0 end
function GetCritChance() return 2.61 end
function GetSpellCritChance() return 3.12 end
function GetHitModifier() return 1 end
function GetSpellHitModifier() return 1 end
function GetSpellBonusHealing() return 0 end
function GetSpellBonusDamage() return 0 end
function GetManaRegen() return 2.4, 0 end
function GetDodgeChance() return 2.9 end
function GetBlockChance() return 5 end
function UnitAttackSpeed() return 2.7 end
function GetInventoryItemLink(_, slot) local id = D.equipped[slot]; return id and link(id) or nil end
function GetInventoryItemDurability(slot) if D.equipped[slot] then return 38, 45 end end
function GetInventorySlotInfo() return 18 end
function ContainerIDToInventoryID(b) return 19 + b end
local function contents(bag) if bag == 0 then return D.bags elseif bag == -1 and D.bankOpen then return D.bank end return {} end
function GetContainerNumSlots(bag) if bag == 0 then return 16 elseif bag == -1 and D.bankOpen then return 24 end return 0 end
function GetContainerItemInfo(bag, slot) local e = contents(bag)[slot]; if e then return nil, e[2], nil, nil, nil, nil, link(e[1]) end end
function GetItemInfo(l)
  local id = tonumber(l) or tonumber(tostring(l):match("item:(%d+)")); local it = D.items[id]; if not it then return nil end
  return it.name, link(id), it.quality, it.ilvl, it.req, "", it.subclass, 1, it.loc, 0, it.sell, it.classID
end
function GetNumQuestLogEntries() return #D.questRows end
function GetQuestLogSelection() return D.sel end
function SelectQuestLogEntry(i) D.sel = i end
function GetQuestLogTitle(i) local q = D.questRows[i]; if q.header then return q.title, 0, nil, true, false end
  return q.title, q.level, nil, false, false, q.complete and 1 or nil, 0, q.id end
function GetNumQuestLeaderBoards(i) return #D.questRows[i].objectives end
function GetQuestLogLeaderBoard(j, i) local o = D.questRows[i].objectives[j]; return o[1], "monster", o[2] end
function GetQuestLogQuestText() return "", D.questRows[D.sel].goal end
function GetQuestLogRewardXP() return D.questRows[D.sel].xp end
function GetQuestLogRewardMoney() return 0 end
function GetNumQuestLogRewards() return 0 end
function GetNumQuestLogChoices() return #D.questRows[D.sel].choices end
function GetQuestLogItemLink(kind, i) if kind == "choice" then return link(D.questRows[D.sel].choices[i]) end end
function GetQuestsCompleted() local t = {} for _, id in ipairs(D.completed) do t[id] = true end return t end
function GetNumTalentTabs() return #D.talents end
function GetTalentTabInfo(t) return D.talents[t][1] end
function GetNumTalents(t) return #D.talents[t][2] end
function GetTalentInfo(t, i) local x = D.talents[t][2][i]; return x[1], nil, x[4], 1, x[2], x[3] end
function GetNumSkillLines() return #D.skills end
function GetSkillLineInfo(i) local s = D.skills[i]; return s[1], s[2] == nil, nil, s[2] and s[2][1], 0, 0, s[2] and s[2][2] end
function GetNumFactions() return 2 end
function GetFactionInfo(i) if i == 1 then return "Alliance", "", 4, 0, 0, 0, nil, nil, true, false, false end
  return "Ironforge", "", 5, 3000, 9000, 4850, nil, nil, false, false, false end
function GetNumSpellTabs() return 1 end
function GetSpellTabInfo() return "Restoration", nil, 0, 2 end
function GetSpellBookItemName(j) return ({ "Healing Wave", "Lesser Healing Wave" })[j], ({ "Rank 3", "" })[j] end
function UnitBuff(_, i) return ({ "Lightning Shield" })[i] end
function GetNumGroupMembers() return 0 end
function IsInRaid() return false end
-- profession window
function GetTradeSkillLine() return "Leatherworking", 62, 75 end
function GetNumTradeSkills() return #D.recipes end
function GetTradeSkillInfo(i) return D.recipes[i][1], D.recipes[i][2] end
-- auction house
AuctionFrame = newFrame("Frame")
function CanSendAuctionQuery() return true, true end
function QueryAuctionItems() D.listed = true; FireEvent("AUCTION_ITEM_LIST_UPDATE") end
function GetNumAuctionItems() return D.listed and #D.auctions or 0 end
function GetAuctionItemInfo(_, i) local a = D.auctions[i]
  return D.items[a[1]].name, nil, a[2], 2, true, 1, nil, 1, 1, a[3], 0, nil, nil, "Seller", nil, 0, a[1], true end
'''


def run():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    ids = set(EQUIPPED.values()) | {i for i, _ in BAGS + BANK} | {a[0] for a in AUCTIONS}
    for q in QUESTS: ids |= set(q[8])
    rows, last = [], None
    for header, title, level, qid, done, objs, goal, xp, choices in QUESTS:
        if header != last:
            rows.append({"header": True, "title": header}); last = header
        rows.append({"title": title, "level": level, "id": qid, "complete": done, "objectives": [list(o) for o in objs],
                     "goal": goal, "xp": xp, "choices": choices})
    mock = {"items": {i: item_record(i) for i in ids}, "equipped": EQUIPPED, "bags": [list(b) for b in BAGS],
            "bank": [list(b) for b in BANK], "questRows": rows, "completed": COMPLETED,
            "talents": [[n, [list(t) for t in ts]] for n, ts in TALENTS], "skills": [[n, list(v) if v else None] for n, v in SKILLS],
            "recipes": [list(r) for r in RECIPES], "auctions": [list(a) for a in AUCTIONS], "locText": LOC_TEXT,
            "now": "2026-11-11 15:40", "printed": [], "sel": 1}
    lua.globals().MOCK = lua.table_from(mock, recursive=True)
    lua.execute(LUA_API)
    src = open(os.path.join(ROOT, "addon", "ClaudeExport", "ClaudeExport.lua"), encoding="utf-8").read()
    lua.execute("local chunk = assert(loadstring(..., 'ClaudeExport.lua')); chunk('ClaudeExport')", src)
    lua.execute("""
      MOCK.bankOpen = true; FireEvent("BANKFRAME_OPENED"); FireEvent("BANKFRAME_CLOSED"); MOCK.bankOpen = false
      FireEvent("TRADE_SKILL_SHOW")
      SlashCmdList.CLAUDEAH()
      SlashCmdList.CLAUDEEXPORT()
    """)
    g = lua.globals()
    text = g.ClaudeExportDB.export
    if not g.MOCK.reloaded: raise SystemExit("/claudeexport did not reload the UI")
    if "(section failed" in text: raise SystemExit("a section failed:\n" + "\n".join(l for l in text.splitlines() if "section failed" in l))
    return text + "\n"


if __name__ == "__main__":
    text = run()
    if "--check" in sys.argv:
        if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != text:
            sys.exit("FAIL: the addon's output differs from test/sample_export.txt (run test/addon_run.py to refresh it)")
        print("ok   addon runs and still produces test/sample_export.txt (%d lines)" % text.count("\n"))
    else:
        open(OUT, "w", encoding="utf-8").write(text)
        print("wrote %s (%d lines)" % (OUT, text.count("\n")))
