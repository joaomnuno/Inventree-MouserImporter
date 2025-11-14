import { useEffect, useRef } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";

interface Props {
  active: boolean;
  onClose: () => void;
  onDetected: (value: string) => void;
}

const BarcodeScanner = ({ active, onClose, onDetected }: Props) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    if (!active || !videoRef.current) {
      return undefined;
    }

    const reader = new BrowserMultiFormatReader();
    let cancelled = false;

    reader.decodeFromVideoDevice(undefined, videoRef.current, (result, error) => {
      if (cancelled) {
        return;
      }
      if (result) {
        onDetected(result.getText());
        onClose();
      }
      if (error?.name === "NotFoundException") {
        return;
      }
      if (error) {
        console.error(error);
      }
    });

    return () => {
      cancelled = true;
      if (typeof (reader as unknown as { stopContinuousDecode?: () => void }).stopContinuousDecode === "function") {
        (reader as unknown as { stopContinuousDecode: () => void }).stopContinuousDecode();
      }
    };
  }, [active, onClose, onDetected]);

  if (!active) {
    return null;
  }

  return (
    <div className="scanner-overlay">
      <div className="scanner-panel">
        <video ref={videoRef} autoPlay muted playsInline className="scanner-video" />
        <button className="secondary" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
};

export default BarcodeScanner;
