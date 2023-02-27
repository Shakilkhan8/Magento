<?php

namespace Emipro\Apichange\Plugin\Api;

use Magento\Catalog\Model\ProductFactory;
use Magento\Sales\Api\Data\OrderItemExtensionFactory;
use Magento\Sales\Api\Data\OrderItemInterface;
use Magento\Sales\Api\Data\OrderItemSearchResultInterface;
use Magento\Sales\Api\OrderItemRepositoryInterface;

class SimpleParentId
{

    /**
     * @var OrderItemExtensionFactory
     */
    protected $orderItemExtensionFactory;

    /**
     * @var ProductFactory
     */
    protected $productFactory;

    /**
     * @var Configproduct;
     */
    private $configproduct;
    /**
     * @param OrderItemExtensionFactory $orderItemExtensionFactory
     * @param ProductFactory $productFactory
     */
    public function __construct(
        OrderItemExtensionFactory $orderItemExtensionFactory,
        \Magento\ConfigurableProduct\Model\ResourceModel\Product\Type\Configurable $configproduct,
        ProductFactory $productFactory
    ) {
        $this->orderItemExtensionFactory = $orderItemExtensionFactory;
        $this->productFactory = $productFactory;
        $this->configproduct = $configproduct;
    }

    /**
     * Add "simple_parent_id" to order item
     *
     * @param OrderItemInterface $orderItem
     *
     * @return OrderItemInterface
     */
    protected function checkParentProduct(OrderItemInterface $orderItem)
    {
        $product = $this->configproduct->getParentIdsByChild($orderItem->getProductId());
        if (isset($product[0])) {
            $orderItemExtension = $this->orderItemExtensionFactory->create();
            $orderItemExtension->setSimpleParentId($product[0]);
            $orderItem->setExtensionAttributes($orderItemExtension);
        }

        return $orderItem;
    }

    /**
     * Add "simple_parent_id" extension attribute to order data object
     * to make it accessible in API data
     *
     * @param OrderItemRepositoryInterface $subject
     * @param OrderItemSearchResultInterface $searchResult
     *
     * @return OrderItemSearchResultInterface
     */
    public function afterGetList(OrderItemRepositoryInterface $subject, OrderItemSearchResultInterface $searchResult)
    {
        $orders = $searchResult->getItems();

        foreach ($orders as &$order) {
            $order = $this->checkParentProduct($order);
        }

        return $searchResult;
    }
}
