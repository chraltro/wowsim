-- ClaudeExport: /claude dumps the whole character as plain text for pasting into Claude.
-- Every API call is wrapped, so a function missing on the Forever client just skips that part.

local ADDON = ...
local unpack = unpack or table.unpack
local floor, format = math.floor, string.format

ClaudeExportDB = ClaudeExportDB or {}

---------------------------------------------------------------------------
-- helpers
---------------------------------------------------------------------------
local function pass(ok, ...)
  if ok then return ... end
  return nil
end

local function try(fn, ...)
  if type(fn) ~= "function" then return nil end
  return pass(pcall(fn, ...))
end

local function clean(s)
  if type(s) ~= "string" then return nil end
  s = s:gsub("|cn.-:", "")              -- new-style named colors
       :gsub("|c%x%x%x%x%x%x%x%x", "")
       :gsub("|r", "")
       :gsub("|T.-|t", "")
       :gsub("|A.-|a", "")
       :gsub("|H.-|h(.-)|h", "%1")
       :gsub("|", "/")
  s = s:gsub("^%s+", ""):gsub("%s+$", "")
  return s
end

local function coins(c)
  if not c or c == 0 then return "0c" end
  local g, s, cp = floor(c / 10000), floor(c / 100) % 100, c % 100
  local t = {}
  if g > 0 then t[#t + 1] = g .. "g" end
  if s > 0 then t[#t + 1] = s .. "s" end
  if cp > 0 then t[#t + 1] = cp .. "c" end
  return table.concat(t, " ")
end

local GetItemInfoX = (C_Item and C_Item.GetItemInfo) or GetItemInfo
local GetDetailedIlvl = (C_Item and C_Item.GetDetailedItemLevelInfo) or GetDetailedItemLevelInfo
local GetSpellNameX = (C_Spell and C_Spell.GetSpellName) or function(id) return (GetSpellInfo(id)) end

local scanner = CreateFrame("GameTooltip", "ClaudeExportScan", nil, "GameTooltipTemplate")

local function tooltipLines(link)
  local lines = {}
  local data = C_TooltipInfo and try(C_TooltipInfo.GetHyperlink, link)
  if data and data.lines then
    for i = 2, #data.lines do
      local L = data.lines[i]
      local l, r = clean(L.leftText), clean(L.rightText)
      if l and l ~= "" then
        lines[#lines + 1] = (r and r ~= "") and (l .. "  " .. r) or l
      end
    end
    return lines
  end
  scanner:SetOwner(WorldFrame, "ANCHOR_NONE")
  scanner:ClearLines()
  if not try(scanner.SetHyperlink, scanner, link) then return lines end
  for i = 2, scanner:NumLines() do
    local lf, rf = _G["ClaudeExportScanTextLeft" .. i], _G["ClaudeExportScanTextRight" .. i]
    local l = lf and clean(lf:GetText())
    local r = rf and rf:IsShown() and clean(rf:GetText())
    if l and l ~= "" then
      lines[#lines + 1] = (r and r ~= "") and (l .. "  " .. r) or l
    end
  end
  return lines
end

local function qualityName(q)
  return q and _G["ITEM_QUALITY" .. q .. "_DESC"] or nil
end

-- One item as text. full=true adds the tooltip (stats, Equip: effects, set bonuses).
local function itemText(link, count, extra, full)
  local name = link:match("%[(.-)%]") or "?"
  local id = link:match("item:(%d+)")
  local enchant = link:match("item:%d+:(%d+)")
  local iName, _, quality, ilvl, reqLevel, _, subclass, _, equipLoc, _, sellPrice, classID = try(GetItemInfoX, link)
  ilvl = try(GetDetailedIlvl, link) or ilvl

  local meta = {}
  if id then meta[#meta + 1] = "id " .. id end
  if ilvl and ilvl > 0 then meta[#meta + 1] = "ilvl " .. ilvl end
  if reqLevel and reqLevel > 1 then meta[#meta + 1] = "req " .. reqLevel end
  if qualityName(quality) then meta[#meta + 1] = qualityName(quality) end
  if subclass and subclass ~= "" then meta[#meta + 1] = subclass end
  if equipLoc == "INVTYPE_NON_EQUIP_IGNORE" then equipLoc = "" end
  if equipLoc and equipLoc ~= "" and _G[equipLoc] then meta[#meta + 1] = _G[equipLoc] end
  if enchant and enchant ~= "0" and enchant ~= "" then meta[#meta + 1] = "enchant " .. enchant end
  if sellPrice and sellPrice > 0 then meta[#meta + 1] = "vendor " .. coins(sellPrice) .. " ea" end
  if extra then meta[#meta + 1] = extra end

  local s = "- " .. (iName or name)
  if count and count > 1 then s = s .. " x" .. count end
  s = s .. " (" .. table.concat(meta, ", ") .. ")"

  local isGear = equipLoc and equipLoc ~= "" and equipLoc ~= "INVTYPE_BAG"
  if full or isGear or classID == 12 then -- 12 = quest items
    for _, l in ipairs(tooltipLines(link)) do s = s .. "\n    " .. l end
  end
  return s
end

---------------------------------------------------------------------------
-- containers
---------------------------------------------------------------------------
local function containerSlots(bag)
  return try(C_Container and C_Container.GetContainerNumSlots, bag) or try(GetContainerNumSlots, bag) or 0
end

local function containerItem(bag, slot)
  if C_Container and C_Container.GetContainerItemInfo then
    local info = try(C_Container.GetContainerItemInfo, bag, slot)
    if info and info.hyperlink then return info.hyperlink, info.stackCount or 1, info.isBound end
    return nil
  end
  local _, count, _, _, _, _, link = try(GetContainerItemInfo, bag, slot)
  if link then return link, count or 1 end
end

-- returns lines, used, total
local function scanBags(bagIDs)
  local order, byLink, used, total = {}, {}, 0, 0
  for _, bag in ipairs(bagIDs) do
    local n = containerSlots(bag)
    total = total + n
    for slot = 1, n do
      local link, count, bound = containerItem(bag, slot)
      if link then
        used = used + 1
        if not byLink[link] then
          byLink[link] = { count = 0, bound = bound }
          order[#order + 1] = link
        end
        byLink[link].count = byLink[link].count + count
      end
    end
  end
  local lines = {}
  for _, link in ipairs(order) do
    local e = byLink[link]
    lines[#lines + 1] = itemText(link, e.count, e.bound and "soulbound" or nil)
  end
  return lines, used, total
end

local function bagIDs()
  local ids = {}
  local last = (NUM_BAG_SLOTS or 4) + (NUM_REAGENTBAG_SLOTS or 0)
  for b = 0, last do ids[#ids + 1] = b end
  return ids
end

local function bankIDs()
  local ids, seen = {}, {}
  local function add(id) if id and not seen[id] then seen[id] = true; ids[#ids + 1] = id end end
  local E = Enum and Enum.BagIndex
  add((E and E.Bank) or BANK_CONTAINER or -1)
  if E then
    for i = 1, 7 do add(E["BankBag_" .. i]) end
    for i = 1, 6 do add(E["CharacterBankTab_" .. i]) end
  end
  local first = (NUM_BAG_SLOTS or 4) + (NUM_REAGENTBAG_SLOTS or 0) + 1
  for b = first, first + (NUM_BANKBAGSLOTS or 6) - 1 do add(b) end
  return ids
end

local function cacheBank()
  local lines, used, total = scanBags(bankIDs())
  if total > 0 then
    ClaudeExportDB.bank = { lines = lines, used = used, total = total, time = date("%Y-%m-%d %H:%M") }
  end
end

---------------------------------------------------------------------------
-- sections
---------------------------------------------------------------------------
local out
local function add(s) out[#out + 1] = s end
local function head(s) add(""); add("## " .. s) end

local function sectionCharacter()
  local name, realm = UnitName("player"), GetRealmName()
  local race, class = UnitRace("player"), UnitClass("player")
  head("Character")
  add(format("%s-%s, level %d %s %s, %s", name or "?", realm or "?", UnitLevel("player") or 0,
    race or "?", class or "?", UnitFactionGroup("player") or "?"))
  local guild, rank = try(GetGuildInfo, "player")
  if guild then add("Guild: " .. guild .. " (" .. (rank or "") .. ")") end
  local xp, xpMax, rested = UnitXP("player"), UnitXPMax("player"), try(GetXPExhaustion)
  if xpMax and xpMax > 0 then
    add(format("XP: %d / %d (%.0f%%)%s", xp, xpMax, xp / xpMax * 100, rested and (", rested " .. rested) or ""))
  end
  add("Gold: " .. coins(GetMoney()))
  local zone, sub = GetZoneText(), GetSubZoneText()
  local loc = zone .. ((sub and sub ~= "") and (" / " .. sub) or "")
  local mapID = C_Map and try(C_Map.GetBestMapForUnit, "player")
  local pos = mapID and try(C_Map.GetPlayerMapPosition, mapID, "player")
  if pos then local x, y = pos:GetXY(); if x then loc = loc .. format(" (%.1f, %.1f)", x * 100, y * 100) end end
  add("Location: " .. loc)
  local bind = try(GetBindLocation)
  if bind then add("Hearthstone: " .. bind) end
  local SI = C_SpecializationInfo
  local spec = try((SI and SI.GetSpecialization) or GetSpecialization)
  if spec then
    local _, sname = try((SI and SI.GetSpecializationInfo) or GetSpecializationInfo, spec)
    if type(sname) == "string" and sname ~= "" then add("Spec: " .. sname) end
  end
  local unspent = try(UnitCharacterPoints, "player")
  if unspent and unspent > 0 then add("Unspent talent points: " .. unspent) end
end

local function sectionStats()
  head("Stats")
  local t = {}
  for i = 1, 5 do
    local _, eff = try(UnitStat, "player", i)
    local n = _G["SPELL_STAT" .. i .. "_NAME"]
    if eff and n then t[#t + 1] = n .. " " .. eff end
  end
  add(table.concat(t, ", "))
  local s = {}
  local function put(label, v, pct) if v and v ~= 0 then s[#s + 1] = label .. " " .. (pct and format("%.2f%%", v) or tostring(floor(v + 0.5))) end end
  put("Health", UnitHealthMax("player"))
  put("Mana", try(UnitPowerMax, "player", 0))
  local _, armor = try(UnitArmor, "player"); put("Armor", armor)
  local base, pos, neg = try(UnitAttackPower, "player"); if base then put("Attack power", base + (pos or 0) + (neg or 0)) end
  put("Melee crit", try(GetCritChance), true)
  put("Ranged crit", try(GetRangedCritChance), true)
  put("Spell crit (nature)", try(GetSpellCritChance, 4), true)
  put("Melee hit bonus", try(GetHitModifier), true)
  put("Spell hit bonus", try(GetSpellHitModifier), true)
  put("Bonus healing", try(GetSpellBonusHealing))
  put("Spell damage (nature)", try(GetSpellBonusDamage, 4))
  local regen, castRegen = try(GetManaRegen)
  if regen then put("Mana regen/5s (not casting)", regen * 5); put("Mana regen/5s (casting)", (castRegen or 0) * 5) end
  put("Dodge", try(GetDodgeChance), true)
  put("Parry", try(GetParryChance), true)
  put("Block", try(GetBlockChance), true)
  local mh, oh = try(UnitAttackSpeed, "player")
  if mh then s[#s + 1] = format("Weapon speed %.2f%s", mh, oh and format(" / %.2f", oh) or "") end
  for _, l in ipairs(s) do add("- " .. l) end
end

local SLOTS = {
  { 1, "Head" }, { 2, "Neck" }, { 3, "Shoulder" }, { 15, "Back" }, { 5, "Chest" }, { 4, "Shirt" },
  { 19, "Tabard" }, { 9, "Wrist" }, { 10, "Hands" }, { 6, "Waist" }, { 7, "Legs" }, { 8, "Feet" },
  { 11, "Finger 1" }, { 12, "Finger 2" }, { 13, "Trinket 1" }, { 14, "Trinket 2" },
  { 16, "Main hand" }, { 17, "Off hand" }, { 18, "Ranged/Relic" },
}

local function sectionGear()
  head("Equipped gear")
  for _, s in ipairs(SLOTS) do
    local link = GetInventoryItemLink("player", s[1])
    if link then
      local cur, max = try(GetInventoryItemDurability, s[1])
      local dur = (cur and max and max > 0) and format("durability %d/%d", cur, max) or nil
      add("[" .. s[2] .. "] " .. itemText(link, 1, dur, true):sub(3))
    elseif s[1] ~= 4 and s[1] ~= 19 and (s[1] ~= 18 or try(GetInventorySlotInfo, "RANGEDSLOT")) then
      add("[" .. s[2] .. "] (empty)")
    end
  end
end

local function sectionBags()
  local lines, used, total = scanBags(bagIDs())
  head(format("Bags (%d/%d slots used)", used, total))
  for b = 1, (NUM_BAG_SLOTS or 4) do
    local link = GetInventoryItemLink("player", (C_Container and C_Container.ContainerIDToInventoryID and
      try(C_Container.ContainerIDToInventoryID, b)) or (try(ContainerIDToInventoryID, b)) or (19 + b))
    if link then add("Bag " .. b .. ": " .. (link:match("%[(.-)%]") or "?") .. " (" .. containerSlots(b) .. " slots)") end
  end
  for _, l in ipairs(lines) do add(l) end
end

local function sectionBank()
  local b = ClaudeExportDB.bank
  if not b then
    head("Bank")
    add("(not cached yet: open your bank once with the addon loaded)")
    return
  end
  head(format("Bank (%d/%d slots, snapshot %s)", b.used, b.total, b.time))
  for _, l in ipairs(b.lines) do add(l) end
end

local function questRewards(questID)
  local r = {}
  local xp = try(GetQuestLogRewardXP, questID)
  if xp and xp > 0 then r[#r + 1] = xp .. " xp" end
  local money = try(GetQuestLogRewardMoney, questID)
  if money and money > 0 then r[#r + 1] = coins(money) end
  local n = try(GetNumQuestLogRewards, questID) or 0
  for i = 1, n do
    local link = try(GetQuestLogItemLink, "reward", i, questID)
    if link then r[#r + 1] = "reward: " .. (link:match("%[(.-)%]") or "?") end
  end
  local c = try(GetNumQuestLogChoices, questID) or 0
  local choices = {}
  for i = 1, c do
    local link = try(GetQuestLogItemLink, "choice", i, questID)
    if link then choices[#choices + 1] = link end
  end
  return r, choices
end

local function addQuest(title, level, questID, complete, group, objectives, summary)
  local tag = {}
  if level and level > 0 then tag[#tag + 1] = "lvl " .. level end
  if questID then tag[#tag + 1] = "id " .. questID end
  if group and group > 0 then tag[#tag + 1] = "group " .. group end
  if complete then tag[#tag + 1] = "COMPLETE" end
  add("- " .. title .. " (" .. table.concat(tag, ", ") .. ")")
  if summary and summary ~= "" then add("    Goal: " .. clean(summary)) end
  for _, o in ipairs(objectives) do add("    [" .. (o.finished and "x" or " ") .. "] " .. (clean(o.text) or "")) end
  if questID then
    if C_QuestLog and C_QuestLog.SetSelectedQuest then try(C_QuestLog.SetSelectedQuest, questID) end
    local r, choices = questRewards(questID)
    if #r > 0 then add("    Rewards: " .. table.concat(r, ", ")) end
    if #choices > 0 then
      add("    Choose one of:")
      for _, link in ipairs(choices) do add("    " .. itemText(link, 1, nil, true):gsub("\n", "\n    ")) end
    end
  end
end

local COLLAPSED = " (COLLAPSED in game, its entries are missing: expand this header and export again)"

local function sectionQuests()
  head("Quest log")
  if C_QuestLog and C_QuestLog.GetNumQuestLogEntries and C_QuestLog.GetInfo then
    local n = try(C_QuestLog.GetNumQuestLogEntries) or 0
    local prev = try(C_QuestLog.GetSelectedQuest)
    for i = 1, n do
      local info = try(C_QuestLog.GetInfo, i)
      if info then
        if info.isHeader then
          add("### " .. (info.title or "?") .. (info.isCollapsed and COLLAPSED or ""))
        elseif not info.isHidden then
          local q = info.questID
          local objs = (q and try(C_QuestLog.GetQuestObjectives, q)) or {}
          local summary
          if q and C_QuestLog.SetSelectedQuest then
            try(C_QuestLog.SetSelectedQuest, q)
            local _, obj = try(GetQuestLogQuestText)
            summary = obj
          end
          local complete = q and try(C_QuestLog.IsComplete, q)
          addQuest(info.title or "?", info.level, q, complete, info.suggestedGroup, objs, summary)
        end
      end
    end
    if prev then try(C_QuestLog.SetSelectedQuest, prev) end
  elseif GetNumQuestLogEntries then
    local n = try(GetNumQuestLogEntries) or 0
    local prev = try(GetQuestLogSelection)
    for i = 1, n do
      local title, level, group, isHeader, collapsed, isComplete, _, questID = try(GetQuestLogTitle, i)
      if title then
        if isHeader then
          add("### " .. title .. (collapsed and COLLAPSED or ""))
        else
          local objs = {}
          for j = 1, (try(GetNumQuestLeaderBoards, i) or 0) do
            local text, _, finished = try(GetQuestLogLeaderBoard, j, i)
            objs[#objs + 1] = { text = text, finished = finished }
          end
          try(SelectQuestLogEntry, i)
          local _, summary = try(GetQuestLogQuestText)
          addQuest(title, level, questID, isComplete == 1 or isComplete == true, group, objs, summary)
        end
      end
    end
    if prev then try(SelectQuestLogEntry, prev) end
  end
end

local function sectionTalents()
  head("Talents")
  local any = false
  -- Classic-style trees
  local tabs = try(GetNumTalentTabs) or 0
  for t = 1, tabs do
    local a, b, c = try(GetTalentTabInfo, t)
    local tabName = type(a) == "string" and a or b   -- (name, ...) on old clients, (id, name, ...) on newer ones
    local spent, picks = 0, {}
    for i = 1, (try(GetNumTalents, t) or 0) do
      local name, _, tier, col, rank, maxRank = try(GetTalentInfo, t, i)
      if name and rank and rank > 0 then
        spent = spent + rank
        picks[#picks + 1] = format("%s %d/%d (row %d)", name, rank, maxRank or 0, tier or 0)
      end
    end
    if tabName then
      any = true
      add(format("### %s (%d points)", tostring(tabName), spent))
      for _, p in ipairs(picks) do add("- " .. p) end
    end
  end
  if any then return end
  -- Modern trait trees
  local configID = C_ClassTalents and try(C_ClassTalents.GetActiveConfigID)
  local cfg = configID and C_Traits and try(C_Traits.GetConfigInfo, configID)
  if cfg and cfg.treeIDs then
    for _, treeID in ipairs(cfg.treeIDs) do
      for _, nodeID in ipairs(try(C_Traits.GetTreeNodes, treeID) or {}) do
        local node = try(C_Traits.GetNodeInfo, configID, nodeID)
        if node and node.activeRank and node.activeRank > 0 and node.activeEntry then
          local entry = try(C_Traits.GetEntryInfo, configID, node.activeEntry.entryID)
          local def = entry and entry.definitionID and try(C_Traits.GetDefinitionInfo, entry.definitionID)
          local spellID = def and (def.spellID or def.overriddenSpellID)
          local name = (def and def.overrideName) or (spellID and try(GetSpellNameX, spellID))
          if name then
            any = true
            add(format("- %s %d/%d", name, node.activeRank, node.maxRanks or node.activeRank))
          end
        end
      end
    end
  end
  if not any then add("(no talents found)") end
end

local function sectionSkills()
  head("Skills and professions")
  local n = try(GetNumSkillLines) or 0
  if n > 0 then
    for i = 1, n do
      local name, isHeader, _, rank, temp, mod, maxRank = try(GetSkillLineInfo, i)
      if name then
        if isHeader then add("### " .. name)
        else add(format("- %s %d/%d%s", name, rank or 0, maxRank or 0, (mod and mod ~= 0) and format(" (%+d)", mod) or "")) end
      end
    end
    return
  end
  local profs = { try(GetProfessions) }
  for _, idx in pairs(profs) do
    local name, _, rank, maxRank = try(GetProfessionInfo, idx)
    if name then add(format("- %s %d/%d", name, rank or 0, maxRank or 0)) end
  end
end

local function sectionReps()
  head("Reputation")
  if C_Reputation and C_Reputation.GetNumFactions and C_Reputation.GetFactionDataByIndex then
    for i = 1, (try(C_Reputation.GetNumFactions) or 0) do
      local f = try(C_Reputation.GetFactionDataByIndex, i)
      if f and f.name then
        if f.isHeader and not f.isHeaderWithRep then add("### " .. f.name .. (f.isCollapsed and COLLAPSED or ""))
        else
          local label = _G["FACTION_STANDING_LABEL" .. (f.reaction or 0)] or ""
          local cur = (f.currentStanding or 0) - (f.currentReactionThreshold or 0)
          local max = (f.nextReactionThreshold or 0) - (f.currentReactionThreshold or 0)
          add(format("- %s: %s %d/%d", f.name, label, cur, max))
        end
      end
    end
  elseif GetNumFactions then
    for i = 1, (try(GetNumFactions) or 0) do
      local name, _, standing, bMin, bMax, val, _, _, isHeader, _, hasRep = try(GetFactionInfo, i)
      if name then
        if isHeader and not hasRep then add("### " .. name)
        else add(format("- %s: %s %d/%d", name, _G["FACTION_STANDING_LABEL" .. (standing or 0)] or "", (val or 0) - (bMin or 0), (bMax or 0) - (bMin or 0))) end
      end
    end
  end
end

local function sectionSpells()
  head("Spellbook")
  if C_SpellBook and C_SpellBook.GetNumSpellBookSkillLines then
    local bank = Enum and Enum.SpellBookSpellBank and Enum.SpellBookSpellBank.Player or 0
    local future = Enum and Enum.SpellBookItemType and Enum.SpellBookItemType.FutureSpell or -1
    for i = 1, (try(C_SpellBook.GetNumSpellBookSkillLines) or 0) do
      local line = try(C_SpellBook.GetSpellBookSkillLineInfo, i)
      if line and not line.shouldHide and not line.offSpecID then
        local names = {}
        for j = line.itemIndexOffset + 1, line.itemIndexOffset + line.numSpellBookItems do
          local it = try(C_SpellBook.GetSpellBookItemInfo, j, bank)
          if it and it.name and it.itemType ~= future and not it.isOffSpec then
            local s = it.name
            if it.subName and it.subName ~= "" then s = s .. " (" .. it.subName .. ")" end
            if it.isPassive then s = s .. " [passive]" end
            names[#names + 1] = s
          end
        end
        add("### " .. (line.name or "?"))
        add(table.concat(names, ", "))
      end
    end
  elseif GetNumSpellTabs then
    for t = 1, (try(GetNumSpellTabs) or 0) do
      local tabName, _, offset, num = try(GetSpellTabInfo, t)
      if tabName then
        local names = {}
        for j = offset + 1, offset + num do
          local name, rank = try(GetSpellBookItemName, j, BOOKTYPE_SPELL or "spell")
          if name then names[#names + 1] = name .. ((rank and rank ~= "") and (" (" .. rank .. ")") or "") end
        end
        add("### " .. tabName)
        add(table.concat(names, ", "))
      end
    end
  end
end

local function sectionBuffs()
  local t = {}
  for i = 1, 40 do
    local name
    if C_UnitAuras and C_UnitAuras.GetAuraDataByIndex then
      local a = try(C_UnitAuras.GetAuraDataByIndex, "player", i, "HELPFUL")
      name = a and a.name
    else
      name = try(UnitBuff, "player", i)
    end
    if not name then break end
    t[#t + 1] = name
  end
  if #t > 0 then head("Active buffs"); add(table.concat(t, ", ")) end
end

local function sectionGroup()
  local n = try(GetNumGroupMembers) or 0
  if n == 0 then return end
  head("Group")
  local prefix = IsInRaid() and "raid" or "party"
  local max = IsInRaid() and n or n - 1
  for i = 1, max do
    local u = prefix .. i
    if UnitExists(u) then
      add(format("- %s, level %d %s %s", UnitName(u) or "?", UnitLevel(u) or 0, UnitRace(u) or "", UnitClass(u) or ""))
    end
  end
end

---------------------------------------------------------------------------
-- build + window
---------------------------------------------------------------------------
local function build()
  out = {}
  add("# WoW: Forever character export")
  add("WoW: Forever = Blizzard's official Classic+ (vanilla world with new content and itemization, modern client). Exported " .. date("%Y-%m-%d %H:%M") .. ".")
  local sections = { sectionCharacter, sectionStats, sectionGear, sectionBags, sectionBank, sectionQuests,
    sectionTalents, sectionSkills, sectionReps, sectionSpells, sectionBuffs, sectionGroup }
  for _, fn in ipairs(sections) do
    local ok, err = pcall(fn)
    if not ok then add("(section failed: " .. tostring(err) .. ")") end
  end
  return table.concat(out, "\n")
end

local frame
local function showWindow(text)
  if not frame then
    frame = CreateFrame("Frame", "ClaudeExportFrame", UIParent, "BasicFrameTemplateWithInset")
    frame:SetSize(760, 540)
    frame:SetPoint("CENTER")
    frame:SetFrameStrata("DIALOG")
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    tinsert(UISpecialFrames, "ClaudeExportFrame")

    local title = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    title:SetPoint("TOP", 0, -6)
    title:SetText("Claude Export  -  Ctrl+C, then paste into Claude")

    local scroll = CreateFrame("ScrollFrame", "ClaudeExportScroll", frame, "UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT", 14, -34)
    scroll:SetPoint("BOTTOMRIGHT", -34, 44)

    local eb = CreateFrame("EditBox", nil, scroll)
    eb:SetMultiLine(true)
    eb:SetAutoFocus(false)
    eb:SetMaxLetters(0)
    eb:SetFontObject(ChatFontNormal)
    eb:SetWidth(700)
    eb:SetScript("OnEscapePressed", function() frame:Hide() end)
    eb:SetScript("OnTextChanged", function(self, user) if user then self:SetText(frame.text or ""); self:HighlightText() end end)
    scroll:SetScrollChild(eb)
    frame.eb = eb

    local btn = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    btn:SetSize(130, 24)
    btn:SetPoint("BOTTOMLEFT", 14, 12)
    btn:SetText("Select all")
    btn:SetScript("OnClick", function() eb:SetFocus(); eb:HighlightText() end)

    local info = frame:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    info:SetPoint("LEFT", btn, "RIGHT", 12, 0)
    frame.info = info
  end
  frame.text = text
  frame.eb:SetText(text)
  frame.info:SetText(format("%d characters. Bank snapshot: %s. /reload also saves this to disk.", #text, ClaudeExportDB.bank and ClaudeExportDB.bank.time or "none yet"))
  frame:Show()
  frame.eb:SetFocus()
  frame.eb:HighlightText()
end

-- warm the item cache so names/tooltips are complete, then build
local function preload()
  if not (C_Item and C_Item.RequestLoadItemDataByID) then return end
  local function req(link) local id = link and tonumber(link:match("item:(%d+)")); if id then C_Item.RequestLoadItemDataByID(id) end end
  for _, s in ipairs(SLOTS) do req(GetInventoryItemLink("player", s[1])) end
  for _, bag in ipairs(bagIDs()) do
    for slot = 1, containerSlots(bag) do req((containerItem(bag, slot))) end
  end
end

local function store(text)
  -- kept in SavedVariables; the game writes that file on /reload or logout
  ClaudeExportDB.export = text
  ClaudeExportDB.exportTime = date("%Y-%m-%d %H:%M:%S")
end

-- /claude: window to copy from.
SLASH_CLAUDEWINDOW1 = "/claude"
SlashCmdList.CLAUDEWINDOW = function()
  if InCombatLockdown() then
    print("|cffd97757Claude Export:|r leave combat first.")
    return
  end
  preload()
  C_Timer.After(0.5, function()
    local text = build()
    store(text)
    showWindow(text)
  end)
end

-- /claudeexport: save and reload the UI, so the export is on disk right away
-- for tools/export_watch.py to turn into a text file.
SLASH_CLAUDEEXPORT1 = "/claudeexport"
SlashCmdList.CLAUDEEXPORT = function()
  if InCombatLockdown() then
    print("|cffd97757Claude Export:|r leave combat first.")
    return
  end
  store(build())
  ReloadUI()
end

local ev = CreateFrame("Frame")
for _, e in ipairs({ "BANKFRAME_OPENED", "BANKFRAME_CLOSED", "PLAYERBANKSLOTS_CHANGED", "BAG_UPDATE_DELAYED" }) do
  pcall(ev.RegisterEvent, ev, e)
end
local bankOpen = false
ev:SetScript("OnEvent", function(_, e)
  if e == "BANKFRAME_OPENED" then
    bankOpen = true
    C_Timer.After(0.3, cacheBank)
  elseif e == "BANKFRAME_CLOSED" then
    bankOpen = false
  elseif bankOpen then
    cacheBank()
  end
end)
