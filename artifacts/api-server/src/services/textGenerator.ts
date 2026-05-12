import fs from "fs";
import path from "path";
import { logger } from "../lib/logger";

const USED_TOPICS_FILE = path.resolve(process.cwd(), "tmp", "used_topics.json");

const BHAKTI_TOPICS: string[] = [
  "Shri Ram ke 108 naam aur unka mahatva. Ram naam japne se man ko shanti milti hai aur jeevan sukhmay ho jata hai. Jai Shri Ram.",
  "Hanuman ji ki shakti aur bhakti. Hanuman chalisa ke paath se sare sankat door hote hain. Bajrang bali ki jai.",
  "Shri Krishna ke jeewan ki leela. Vrindavan mein Krishna ne bansuri bajaakar sabka man mohit kiya. Radhe Radhe.",
  "Maa Durga ke nau roop aur unki mahima. Navratri mein mata ki aradhna se jeewan mein aashirwad milta hai. Jai Mata Di.",
  "Shiv bhakti ka mahatva. Om Namah Shivay ka jaap karne se jeewan ke sare kashta door hote hain. Har Har Mahadev.",
  "Ganesh ji ki pooja aur unka mahatva. Har shubh kaam ki shuruvat Ganesh vandana se hoti hai. Jai Ganesh.",
  "Bhagwad Geeta ka gyan. Shri Krishna ne Arjun ko karmayog ka sandesh diya jo aaj bhi praasangik hai.",
  "Maa Lakshmi ki kripa se ghar mein samridhi aati hai. Shukrawar ko Lakshmi pooja karne se dhan aur sukh milta hai.",
  "Saraswati mata gyaan ki devi hain. Vidyarthi jinke charan sparsh karte hain unhe vidya aur buddhi prapt hoti hai.",
  "Sai Baba ki leela aur unka sandesh sabka malik ek hai. Shirdi Sai baba ke bhakton par unki kripa sada bani rahti hai.",
  "Tirupati Balaji ke darshan se jeevan mein mangal hota hai. Venkateswara swami ke charan mein sarve sukh hain.",
  "Mata Vaishno Devi ki yatra aur unki mahima. Jammu ki pahado mein mata ka dham hai jahan har manokamanaa poori hoti hai.",
  "Shrimad Bhagavat ka paath karne se moksh ki praapti hoti hai. Bhagwat katha sunne se man pavitra ho jata hai.",
  "Radha Krishna ki prem leela Vrindavan mein abhi bhi jeevit hai. Braj ki galiyon mein unki yaad basi hai.",
  "Mahakal Ujjain ke adhipati hain. Kaal ke upar bhi inka adhikar hai isliye inhe Mahakal kaha jata hai. Om Namah Shivay.",
  "Ramayan ki katha mein maryada purushottam Ram ka adarsh jeevan samahit hai. Unka charitra aaj bhi prerana deta hai.",
  "Mahabharat ka gyan aur dharma ki vijay. Satya aur dharma ke maarg par chalne wala kabhi nahi harta. Jai Shri Krishna.",
  "Navagraha pooja se jeevan ke dosh door hote hain. Surya deva ki aradhna se swasthya aur tej prapt hota hai.",
  "Sankat Mochan Hanuman ka naam lene se sab sankat door ho jate hain. Mangalvaar ko Hanuman ji ki aradhna vishesh phal deti hai.",
  "Shiv Puran ke anusar Mahadev sab devon mein shreshtha hain. Unki aradhna se jeewan ke sare dukh khatam hote hain.",
  "Bhakti marg mein param shanti hai. Ishwar ki bhakti karne se antakaraan shuddh hota hai aur mukti milti hai.",
  "Tulsi das ji ne Ramcharitmanas likhkar Ram katha ko ghar ghar pahunchaya. Unka yeh granth aaj bhi lokapriya hai.",
  "Amarnath yatra mein Shivling ke darshan se moksh milta hai. Yeh sthan Shiva ka pawan dham hai Himalaya mein.",
  "Puri Jagannath Mandir mein Rath Yatra ek anokha utsav hai jisme lakhon bhakt bhaag lete hain. Jai Jagannath.",
  "Dwarkadhish shri Krishna ka janm Mathura mein hua aur unhone Dwarika mein apna rajya sthapit kiya. Jai Dwarkadhish.",
  "Kashi Vishwanath ke darshan karna jeevan ka sabse bada punya hai. Banaras mein Ganga snan aur Shiv darshan se mukti milti hai.",
  "Ashtavinayak yatra Maharashtra mein Ganesh ji ke aath roopon ke darshan ka avsar deti hai. Jai Ganpati Bappa.",
  "Char Dham yatra mein Badrinath Kedarnath Gangotri Yamunotri ke darshan se jeevan safal hota hai.",
  "Maa Kali ki aradhna se shatru nasha hota hai aur bhakt ki raksha hoti hai. Kali mata ki jai.",
  "Guru ki mahima guru bin gyaan nahi milta. Guru ko ishwar ka roop mana jata hai aur unki seva param punya hai.",
];

function loadUsedTopics(): Set<number> {
  try {
    const dir = path.dirname(USED_TOPICS_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    if (!fs.existsSync(USED_TOPICS_FILE)) return new Set();
    const data = JSON.parse(fs.readFileSync(USED_TOPICS_FILE, "utf-8"));
    return new Set(data as number[]);
  } catch {
    return new Set();
  }
}

function saveUsedTopics(used: Set<number>): void {
  try {
    fs.writeFileSync(USED_TOPICS_FILE, JSON.stringify([...used]));
  } catch (err) {
    logger.warn({ err }, "Could not save used topics");
  }
}

export function getNextBhaktiText(): string {
  const used = loadUsedTopics();

  if (used.size >= BHAKTI_TOPICS.length) {
    logger.info("All topics used, resetting pool");
    used.clear();
  }

  const available = BHAKTI_TOPICS
    .map((_, i) => i)
    .filter((i) => !used.has(i));

  const randomIdx = available[Math.floor(Math.random() * available.length)]!;
  used.add(randomIdx);
  saveUsedTopics(used);

  const text = BHAKTI_TOPICS[randomIdx]!;
  logger.info({ topicIndex: randomIdx, usedCount: used.size, total: BHAKTI_TOPICS.length }, "Bhakti topic selected");
  return text;
}

export function getRemainingTopicsCount(): number {
  const used = loadUsedTopics();
  return BHAKTI_TOPICS.length - used.size;
}

export function resetTopics(): void {
  try {
    if (fs.existsSync(USED_TOPICS_FILE)) fs.unlinkSync(USED_TOPICS_FILE);
    logger.info("Topic pool reset");
  } catch {}
}
