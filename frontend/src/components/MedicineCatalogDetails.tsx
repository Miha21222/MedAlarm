import { ExternalLink, Landmark, ShieldCheck } from "lucide-react";
import { useAppSettings } from "../contexts/AppSettingsContext";
import type { MedicineCatalogReference } from "../types";

const DATASET_URL = "https://data.gov.ua/dataset/reestr_likarskyh_zasobiv_moz";

function safeExternalUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export function MedicineCatalogDetails({ catalog, condensed = false }: {
  catalog: MedicineCatalogReference;
  condensed?: boolean;
}) {
  const { t } = useAppSettings();
  const instructionUrl = safeExternalUrl(catalog.instruction_url);
  const fields = [
    [t("inn"), catalog.inn],
    [t("formAndPackage"), catalog.form],
    [t("activeIngredients"), catalog.active_ingredients],
    [t("therapeuticGroup"), catalog.pharmacotherapeutic_group],
    [t("manufacturer"), catalog.manufacturer],
    [t("applicant"), catalog.applicant],
    [t("registration"), catalog.registration_number],
    [t("registrationValidity"), [catalog.valid_from, catalog.valid_until].filter(Boolean).join(" — ") || null],
    [t("earlyTermination"), catalog.early_termination],
    [t("atc"), catalog.atc_codes],
    [t("dispensing"), catalog.dispensing_conditions],
  ].filter((field): field is [string, string] => Boolean(field[1]));

  return (
    <article className={`catalog-details${condensed ? " condensed" : ""}`}>
      <header>
        <span><Landmark size={18} /></span>
        <div>
          <small>{t("officialData")}</small>
          <strong>{catalog.trade_name}</strong>
        </div>
      </header>
      <dl>
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {instructionUrl ? (
        <a className="catalog-instruction-link" href={instructionUrl} target="_blank" rel="noreferrer noopener">
          <ExternalLink size={16} />
          {t("openInstruction")}
        </a>
      ) : null}
      <p className="catalog-disclaimer"><ShieldCheck size={16} />{t("medicalDisclaimer")}</p>
      <a className="catalog-attribution" href={DATASET_URL} target="_blank" rel="noreferrer noopener">
        {t("sourceAttribution")}
      </a>
    </article>
  );
}
