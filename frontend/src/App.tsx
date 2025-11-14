import { useCallback, useState } from "react";
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
  stock?: number;
  lead_time_weeks?: number;
  parameters?: Parameter[];
  price_breaks?: PriceBreak[];
};

const defaultPart: PartResponse = {
  name: "",
  supplier: "",
  parameters: [],
  price_breaks: []
};

function App() {
  const [supplier, setSupplier] = useState<Supplier>("mouser");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [part, setPart] = useState<PartResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [scannerActive, setScannerActive] = useState(false);

  const fetchPart = useCallback(async (value: string) => {
    if (!value) {
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`/api/search/${supplier}/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ part_number: value })
      });
      if (!response.ok) {
        throw new Error("Unable to fetch part information");
      }
      const data: PartResponse = await response.json();
      setPart({ ...defaultPart, ...data });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }, [supplier]);

  const handleImport = async () => {
    if (!part) {
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch("/api/import/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(part)
      });
      if (!response.ok) {
        const detail = await response.json();
        throw new Error(detail.detail || "Failed to import part");
      }
      setMessage("Part created in InvenTree");
      setPart(null);
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
              onChange={() => setSupplier("mouser")}
            />
            Mouser
          </label>
          <label>
            <input
              type="radio"
              value="digikey"
              checked={supplier === "digikey"}
              onChange={() => setSupplier("digikey")}
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

      {part && (
        <section className="card">
          <h2>Review & Edit</h2>
          <div className="form-grid">
            <label>
              Name
              <input value={part.name} onChange={(event) => setPart({ ...part, name: event.target.value })} />
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
              InvenTree Category ID
              <input
                type="number"
                value={part.category_id ?? ""}
                onChange={(event) =>
                  setPart({ ...part, category_id: event.target.value ? Number(event.target.value) : undefined })
                }
              />
            </label>
          </div>

          <div className="metadata">
            {part.datasheet_url && (
              <a href={part.datasheet_url} target="_blank" rel="noreferrer">
                Datasheet
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
