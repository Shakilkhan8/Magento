<?php

namespace Emipro\Apichange\Model;

use Emipro\Apichange\Api\OrderstatusInterface;

class Orderstatus implements OrderstatusInterface
{
    protected $statusCollectionFactory;

    public function __construct(
        \Magento\Sales\Model\ResourceModel\Order\Status\CollectionFactory $statusCollectionFactory
    ) {
        $this->statusCollectionFactory = $statusCollectionFactory;
    }

    public function orderstatus()
    {
        $options = $this->statusCollectionFactory->create()->toOptionArray();
        return $options;
    }
}
