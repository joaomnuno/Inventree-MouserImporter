import { useCallback, useEffect, useState } from "react";
import BarcodeScanner from "./components/BarcodeScanner";

type Supplier = "mouser" | "digikey";

type Parameter = {
  name: string;
  value: string;
};

type PriceBreak = {
  quantity: number;
  price: number;
  currency: string;
};

type PartResponse = {
  name: string;
  description?: string;
  manufacturer?: string;
  mpn?: string;
  supplier: string;
  supplier_company_id?: number;
  supplier_sku?: string;
  category_id?: number;
  category_path?: string[];
  datasheet_url?: string;
  image_url?: string;
  supplier_link?: string;
  stock?: number;
  lead_time_weeks?: number;
  parameters?: Parameter[];
  price_breaks?: PriceBreak[];
};

const defaultPart: PartResponse = {
  name: "",
  supplier: "",
  parameters: [],
  price_breaks: [],
  category_path: [],
  supplier_link: ""
};

type ImporterPreview = {
  supplier: Supplier;
  supplier_name: string;
  part_number: string;
  match_count: number;
  part: PartResponse;
  matched_category?: string[] | null;
  warnings?: string[];
};

type LookupContext = {
  supplier: Supplier;
  partNumber: string;
};

const getCookie = (name: string) => {
  if (typeof document === "undefined") {
    return null;
  }
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(`${name}=`)) {
      return decodeURIComponent(trimmed.substring(name.length + 1));
    }
  }
  return null;
};

const getCsrfToken = () => getCookie("csrftoken");

function App() {
  const [supplier, setSupplier] = useState<Supplier>("mouser");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [part, setPart] = useState<PartResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [previewWarnings, setPreviewWarnings] = useState<string[]>([]);
  const [matchedCategory, setMatchedCategory] = useState<string[] | null>(null);
  const [lastLookup, setLastLookup] = useState<LookupContext | null>(null);
  const [scannerActive, setScannerActive] = useState(false);

  const resetPreview = useCallback(() => {
    setPart(null);
    setPreviewWarnings([]);
    setMatchedCategory(null);
    setLastLookup(null);
  }, []);

  const handleSupplierSwitch = (nextSupplier: Supplier) => {
    setSupplier(nextSupplier);
    resetPreview();
  };

  useEffect(() => {
    fetch("/api/health/", { credentials: "include" }).catch(() => {
      /* Ignore health check errors, they will surface on real requests */
    });
  }, []);

  const fetchPart = useCallback(async (value: string) => {
    if (!value) {
      return;
    }
    setLoading(true);
    setMessage(null);
    setPreviewWarnings([]);
    setMatchedCategory(null);
    try {
      const csrfToken = getCsrfToken();
      const response = await fetch(`/api/importer/preview/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {})
        },
        body: JSON.stringify({ supplier, part_number: value })
      });
      if (!response.ok) {
        let errorMessage = "Unable to fetch part information";
        try {
          const detail = await response.json();
          if (detail?.detail) {
            errorMessage = detail.detail;
          }
        } catch (error) {
          /* ignore json errors */
        }
        throw new Error(errorMessage);
      }
      const data: ImporterPreview = await response.json();
      setPart({ ...defaultPart, ...data.part });
      setPreviewWarnings(data.warnings ?? []);
      setMatchedCategory(data.matched_category ?? null);
      setLastLookup({ supplier: data.supplier, partNumber: data.part_number });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unexpected error");
      setLastLookup(null);
    } finally {
      setLoading(false);
    }
  }, [supplier]);

  const handleImport = async () => {
    if (!part || !lastLookup) {
      setMessage("Run a preview before importing.");
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const csrfToken = getCsrfToken();
      const overrides: Record<string, unknown> = {};
      if (part.description) overrides.description = part.description;
      if (part.manufacturer) overrides.manufacturer = part.manufacturer;
      if (part.mpn) overrides.mpn = part.mpn;
      if (part.supplier_sku) overrides.supplier_sku = part.supplier_sku;
      if (part.datasheet_url) overrides.datasheet_url = part.datasheet_url;
      if (part.image_url) overrides.image_url = part.image_url;
      if (part.category_path && part.category_path.length > 0) {
        overrides.category_path = part.category_path;
      }
      if (part.parameters && part.parameters.length > 0) {
        overrides.parameters = part.parameters;
      }
      if (part.price_breaks && part.price_breaks.length > 0) {
        overrides.price_breaks = part.price_breaks;
      }

      const response = await fetch("/api/importer/import/", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {})
        },
        body: JSON.stringify({
          supplier: lastLookup.supplier,
          part_number: lastLookup.partNumber,
          overrides
        })
      });
      if (!response.ok) {
        const detail = await response.json();
        throw new Error(detail.detail || "Failed to import part");
      }
      const outcome = await response.json();
      setMessage(outcome.detail || "Importer finished");
      resetPreview();
      setInput("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  const updateParameter = (index: number, field: keyof Parameter, value: string) => {
    if (!part?.parameters) return;
    const updated = [...part.parameters];
    updated[index] = { ...updated[index], [field]: value };
    setPart({ ...part, parameters: updated });
  };

  const addParameter = () => {
    if (!part) return;
    const parameters = [...(part.parameters || []), { name: "", value: "" }];
    setPart({ ...part, parameters });
  };

  const handleDetected = useCallback(
    (value: string) => {
      setScannerActive(false);
      setInput(value);
      fetchPart(value);
    },
    [fetchPart]
  );

  return (
    <main className="app">
      <header>
        <h1>InvenTree Part Importer</h1>
        <p>Scan or enter a Mouser / Digi-Key reference and import in a single flow.</p>
      </header>

      <section className="card">
        <div className="supplier-toggle">
          <label>
            <input
              type="radio"
              value="mouser"
              checked={supplier === "mouser"}
              onChange={() => handleSupplierSwitch("mouser")}
            />
            Mouser
          </label>
          <label>
            <input
              type="radio"
              value="digikey"
              checked={supplier === "digikey"}
              onChange={() => handleSupplierSwitch("digikey")}
            />
            Digi-Key
          </label>
        </div>

        <div className="search-row">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && fetchPart(input)}
            placeholder="Scan or type the part number"
          />
          <button disabled={loading} onClick={() => fetchPart(input)}>
            Search
          </button>
          <button className="secondary" onClick={() => setScannerActive(true)}>
            Scan with camera
          </button>
        </div>
      </section>

      {message && <div className="alert">{message}</div>}

      {part && previewWarnings.length > 0 && (
        <div className="alert warning">
          {previewWarnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      )}

      {part && (
        <section className="card">
          <h2>Review & Edit</h2>
          {matchedCategory && matchedCategory.length > 0 && (
            <div className="info-banner">
              <span>Suggested category</span>
              <strong>{matchedCategory.join(" / ")}</strong>
            </div>
          )}
          <div className="form-grid">
            <label>
              Name
              <input value={part.name} disabled />
              <small>The importer uses the MPN as the InvenTree part name.</small>
            </label>
            <label>
              Description
              <textarea
                value={part.description ?? ""}
                onChange={(event) => setPart({ ...part, description: event.target.value })}
              />
            </label>
            <label>
              Manufacturer
              <input
                value={part.manufacturer ?? ""}
                onChange={(event) => setPart({ ...part, manufacturer: event.target.value })}
              />
            </label>
            <label>
              MPN
              <input value={part.mpn ?? ""} onChange={(event) => setPart({ ...part, mpn: event.target.value })} />
            </label>
            <label>
              Supplier SKU
              <input
                value={part.supplier_sku ?? ""}
                onChange={(event) => setPart({ ...part, supplier_sku: event.target.value })}
              />
            </label>
            <label>
              Category Path Override
              <input
                value={(part.category_path ?? []).join(" / ")}
                onChange={(event) => {
                  const path = event.target.value
                    .split("/")
                    .map((item) => item.trim())
                    .filter(Boolean);
                  setPart({ ...part, category_path: path });
                }}
                placeholder="Electronics / Connectors / Headers"
              />
            </label>
          </div>

          <div className="metadata">
            {part.datasheet_url && (
              <a href={part.datasheet_url} target="_blank" rel="noreferrer">
                Datasheet
              </a>
            )}
            {part.supplier_link && (
              <a href={part.supplier_link} target="_blank" rel="noreferrer">
                Supplier page
              </a>
            )}
            {part.image_url && <img src={part.image_url} alt="part" />}
          </div>

          <div className="parameters">
            <div className="section-header">
              <h3>Parameters</h3>
              <button className="secondary" onClick={addParameter}>
                Add parameter
              </button>
            </div>
            {(part.parameters || []).map((parameter, index) => (
              <div key={`${parameter.name}-${index}`} className="parameter-row">
                <input
                  value={parameter.name}
                  onChange={(event) => updateParameter(index, "name", event.target.value)}
                  placeholder="Name"
                />
                <input
                  value={parameter.value}
                  onChange={(event) => updateParameter(index, "value", event.target.value)}
                  placeholder="Value"
                />
              </div>
            ))}
          </div>

          {part.price_breaks && part.price_breaks.length > 0 && (
            <div className="price-table">
              <h3>Pricing</h3>
              <table>
                <thead>
                  <tr>
                    <th>Qty</th>
                    <th>Price ({part.price_breaks[0].currency})</th>
                  </tr>
                </thead>
                <tbody>
                  {part.price_breaks.map((breakPoint) => (
                    <tr key={breakPoint.quantity}>
                      <td>{breakPoint.quantity}</td>
                      <td>{breakPoint.price.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <button disabled={loading} onClick={handleImport} className="primary">
            Import to InvenTree
          </button>
        </section>
      )}

      <BarcodeScanner active={scannerActive} onClose={() => setScannerActive(false)} onDetected={handleDetected} />
    </main>
  );
}

export default App;
