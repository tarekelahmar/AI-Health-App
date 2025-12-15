import { FC } from "react";

export const SafetyBanner: FC = () => {
  return (
    <div className="mb-4 rounded border border-red-500 bg-red-50 p-3 text-sm">
      <div className="font-semibold">Not medical advice</div>
      <div className="mt-1 text-gray-700">
        This app provides informational insights only. It does not diagnose or treat conditions.
        If you have severe symptoms or safety concerns, seek professional medical help.
      </div>
    </div>
  );
};

