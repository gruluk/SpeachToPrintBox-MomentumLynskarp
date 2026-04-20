export default function CheckoutDoneScreen({ name, onDone }) {
  return (
    <div className="screen center">
      <h2>Takk for at du kom, {name}!</h2>
      <p className="status-text">
        Du er nå sjekket ut. Ha en fin dag videre!
      </p>
      <button className="btn-primary" onClick={onDone}>Ferdig</button>
    </div>
  )
}
