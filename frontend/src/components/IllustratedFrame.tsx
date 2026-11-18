import type { ReactNode } from "react";
import "./IllustratedFrame.css";

interface IllustratedFrameProps {
  asset: string;
  className: string;
  children: ReactNode;
}

function IllustratedFrame({ asset, className, children }: IllustratedFrameProps) {
  return (
    <div className={`illustrated-frame ${className}`}>
      <img className="illustrated-frame-art" src={asset} alt="" aria-hidden="true" />
      <div className="illustrated-frame-content">{children}</div>
    </div>
  );
}

export default IllustratedFrame;
