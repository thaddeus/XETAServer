<?php
use Ratchet\MessageComponentInterface;
use Ratchet\ConnectionInterface;
use Ratchet\Server\IoServer;
use Ratchet\WebSocket\WsServer;
use Ratchet\Http\HttpServer;

    require __DIR__ . '/vendor/autoload.php';

class Xeta implements MessageComponentInterface {
    protected $clients;

    public function __construct() {
        $this->clients = new \SplObjectStorage;
    }

    public function onOpen(ConnectionInterface $conn) {
        $this->clients->attach($conn);
        print("CONNECTION RECEIVED\n");
        //Create init packet
        $message = array();
        $message['packetType'] = 0;
        //Send init packet
        $conn->send(json_encode($message));
    }

    public function onMessage(ConnectionInterface $from, $msg) {
        print("RECIEVE << " . $msg . "\n");
        $packet = json_decode($msg);
        print("Connection initialized from " . $packet->machineName . "\n");
        $from->machine = new \StdClass;
        $from->machine->name = $packet->machineName;
    }

    public function onClose(ConnectionInterface $conn) {
    	print("Connection closed from " . $conn->machine->name . "\n");
        $this->clients->detach($conn);

    }

    public function onError(ConnectionInterface $conn, \Exception $e) {
        $conn->close();
    }
}

    // Run the server application through the WebSocket protocol on port 47895
    $server = IoServer::factory(
        new HttpServer(
            new WsServer(
                new Xeta()
            )
        ),
        47895, '0.0.0.0'
    );
    $server->run();
?>