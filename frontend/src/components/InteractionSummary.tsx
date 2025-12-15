import { FC } from "react";

type Props = {
  confounder: string;
  message: string;
};

export const InteractionSummary: FC<Props> = ({ confounder, message }) => {
  return (
    <div className="mt-3 rounded border border-yellow-400 bg-yellow-50 p-3 text-sm">
      <strong>Interaction detected:</strong>
      <div className="mt-1">
        {message}
      </div>
      <div className="mt-1 italic text-gray-600">
        Tip: Try adjusting <b>{confounder}</b> and re-evaluate.
      </div>
    </div>
  );
};

