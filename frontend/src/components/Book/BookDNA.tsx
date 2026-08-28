import "./BookDNA.css";

import dnaIcon from "../../assets/dna.png";
import romanceIcon from "../../assets/romance.png";
import fantasyIcon from "../../assets/fantasy.png";
import thrillerIcon from "../../assets/thriller.png";
import scifiIcon from "../../assets/scifi.png";
import horrorIcon from "../../assets/horror.png";
import nonfictionIcon from "../../assets/nonfiction.png";
import yaIcon from "../../assets/ya.png";

interface Props {
  dna: Record<string, number> | null;
}

const categories = [
  {
    key: "romance",
    name: "Romance",
    icon: romanceIcon,
  },
  {
    key: "fantasy_romantasy",
    name: "Fantasia & Romantasia",
    icon: fantasyIcon,
  },
  {
    key: "thriller_mystery_crime",
    name: "Thriller & Policial",
    icon: thrillerIcon,
  },
  {
    key: "science_fiction",
    name: "Ficção Científica",
    icon: scifiIcon,
  },
  {
    key: "horror",
    name: "Terror & Horror",
    icon: horrorIcon,
  },
  {
    key: "personal_development_nonfiction",
    name: "Não Ficção",
    icon: nonfictionIcon,
  },
  {
    key: "young_adult",
    name: "Jovem Adulto",
    icon: yaIcon,
  },
];

function BookDNA({ dna }: Props) {
  if (!dna) {
    return null;
  }

  const sortedCategories = [...categories].sort(
    (a, b) => (dna[b.key] ?? 0) - (dna[a.key] ?? 0)
  );

  const mainCategories = sortedCategories.slice(0, 3);
  const secondaryCategories = sortedCategories.slice(3);

  return (
    <section className="book-dna">

      <div className="book-dna-title">
        <img
          src={dnaIcon}
          alt=""
          className="dna-title-icon"
        />

        <h3>BOOK DNA</h3>
      </div>

      <div className="dna-row dna-main-row">
        {mainCategories.map((category) => (
          <div
            className="dna-category dna-main-category"
            key={category.key}
          >
            <img
              src={category.icon}
              alt=""
              className="dna-category-icon"
            />

            <span>{category.name}</span>
            <strong>{dna[category.key] ?? 0}%</strong>
          </div>
        ))}
      </div>

      <div className="dna-row dna-secondary-row">
        {secondaryCategories.map((category) => (
          <div
            className="dna-category dna-secondary-category"
            key={category.key}
          >
            <img
              src={category.icon}
              alt=""
              className="dna-category-icon"
            />

            <span>{category.name}</span>
            <strong>{dna[category.key] ?? 0}%</strong>
          </div>
        ))}
      </div>

    </section>
  );
}

export default BookDNA;