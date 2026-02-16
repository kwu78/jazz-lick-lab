export default function ErrorBox({ message }: { message: string }) {
  return (
    <div className="border border-red-300 bg-red-50 text-red-900 rounded px-4 py-3 text-sm mb-4">
      {message}
    </div>
  );
}
